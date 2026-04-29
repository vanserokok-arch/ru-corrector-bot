"""Tests for reset correction engine architecture."""

import pytest

import ru_corrector.rules.legal as legal_rules
from ru_corrector.core.engine import CorrectionEngine
from ru_corrector.core.models import CorrectionResult
from ru_corrector.providers.mock import MockProvider
from ru_corrector.rules.base import apply_base
from ru_corrector.rules.legal import apply_legal
from ru_corrector.rules.legal_money import normalize_money
from ru_corrector.rules.strict import apply_strict
from ru_corrector.rules.typo import apply_typo
from tests.fixtures.legal_stress_cases import LEGAL_STRESS_EXPECTED, LEGAL_STRESS_RAW


@pytest.fixture(autouse=True)
def _disable_openai_refiner_by_default(monkeypatch):
    monkeypatch.setattr(legal_rules.config, "ENABLE_OPENAI_REFINER", False)


class _ErrProvider:
    def check(self, text: str):
        raise RuntimeError("provider down")


class _CountProvider:
    def __init__(self):
        self.calls = 0

    def check(self, text: str):
        self.calls += 1
        return []


class _Edit:
    def __init__(self, offset: int, length: int, replacement: str):
        self.offset = offset
        self.length = length
        self.replacement = replacement


class _TelegramLikeBrokenProvider:
    def check(self, text: str):
        replacements = {
            "гк рф": "к рф",
            "прошу": "п рошу",
            "вследствие": "в следствие",
        }
        edits = []
        for original, replacement in replacements.items():
            start = 0
            while True:
                offset = text.find(original, start)
                if offset == -1:
                    break
                edits.append(_Edit(offset=offset, length=len(original), replacement=replacement))
                start = offset + len(original)
        return edits


def test_base_applies_provider_edit():
    provider = MockProvider([_Edit(offset=0, length=5, replacement="Привет")])
    assert apply_base("Првет мир", provider=provider) == "Привет мир"


def test_base_does_not_apply_legal_typography():
    provider = MockProvider([])
    result = apply_base("ст. 15 ГК РФ", provider=provider)
    assert "ст. 15" in result
    assert "ст.\u00a015" not in result


def test_base_provider_error_no_crash():
    result = apply_base("Текст", provider=_ErrProvider())
    assert result == "Текст"


def test_legal_article_nbsp():
    assert "ст.\u00a015" in apply_legal("ст. 15 ГК РФ", provider=MockProvider([]))


def test_legal_article_with_suffix():
    assert "ст.\u00a015а" in apply_legal("ст. 15а", provider=MockProvider([]))


def test_legal_point_nbsp():
    assert "п.\u00a02.1" in apply_legal("п. 2.1 договора", provider=MockProvider([]))


def test_legal_subpoint_nbsp():
    assert "пп.\u00a02.1" in apply_legal("пп. 2.1 договора", provider=MockProvider([]))


def test_legal_part_and_article_nbsp():
    result = apply_legal("ч. 3 ст. 15", provider=MockProvider([]))
    assert "ч.\u00a03" in result
    assert "ст.\u00a015" in result


def test_legal_numero_with_date_tail():
    result = apply_legal("№ 123/2026 от 01.01.2026", provider=MockProvider([]))
    assert "№\u00a0123/2026 от 1 января 2026 года" in result


def test_legal_case_number_not_broken():
    result = apply_legal("дело № А56-12345/2026", provider=MockProvider([]))
    assert "Дело №\u00a0А56-12345/2026" in result


def test_legal_money_nbsp():
    result = apply_legal("3200000 руб 25 коп", provider=MockProvider([]))
    assert "3 200 000 (Три миллиона двести тысяч) рублей" in result
    assert "25 (Двадцать пять) копеек" in result


def test_legal_quotes_and_dash():
    result = apply_legal('Он сказал "привет". Москва - Петербург', provider=MockProvider([]))
    assert "«привет»" in result
    assert "Москва — Петербург" in result


def test_legal_hyphenated_word_unchanged():
    assert apply_legal("Северо-западный", provider=MockProvider([])) == "Северо-западный"


def test_legal_protect_unprotect_roundtrip():
    src = (
        "Цена 3 200 000 (Три миллиона двести тысяч) рублей 25 (Двадцать пять) копеек "
        "по договору от 12 апреля 2024 года, ст. 450 ГК РФ, № 123/2024."
    )

    protected, mapping = legal_rules.protect_legal_entities(src)

    assert "__LEGAL_ENTITY_0__" in protected
    assert mapping
    assert legal_rules.unprotect_legal_entities(protected, mapping) == src


def test_legal_rules_only_behavior_when_openai_refiner_disabled(monkeypatch):
    monkeypatch.setattr(legal_rules.config, "ENABLE_OPENAI_REFINER", False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    src = "прошу взыскать сумму 3200000 руб по ст. 450 гк рф"

    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")

    assert result == (
        "Прошу взыскать сумму в размере 3 200 000 (Три миллиона двести тысяч) рублей "
        "по ст. 450 ГК РФ."
    )
    assert legal_rules.openai_refine("Текст без вызова OpenAI") == "Текст без вызова OpenAI"


def test_legal_mocked_openai_refiner_restores_protected_entities(monkeypatch):
    def fake_refine(text: str) -> str:
        assert "__LEGAL_ENTITY_0__" in text
        assert "3 200 000" not in text
        return text.replace(
            "номер __LEGAL_ENTITY_3__ ответчик",
            "номер __LEGAL_ENTITY_3__, ответчик",
        )

    monkeypatch.setattr(legal_rules, "openai_refine", fake_refine)
    src = (
        "прошу взыскать сумму 3200000 руб 25 коп по ст. 450 гк рф "
        "от 12.04.2024 номер № 123/2024 ответчик нарушил обязательства"
    )

    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")

    assert (
        "3 200 000 (Три миллиона двести тысяч) рублей 25 (Двадцать пять) копеек"
        in result
    )
    assert "12 апреля 2024 года" in result
    assert "ст. 450 ГК РФ" in result
    assert "№ 123/2024" in result
    assert "№ 123/2024, ответчик" in result
    assert "__LEGAL_ENTITY_" not in result
    assert ", ," not in result
    assert " ." not in result
    assert " ," not in result


def test_strict_preserves_newlines_and_lists():
    text = "1) Первый пункт\n2) Второй пункт\n\n3) Третий пункт"
    result = apply_strict(text, provider=MockProvider([]))
    assert result.count("\n") == text.count("\n")
    assert "1) Первый пункт" in result


def test_strict_cleans_spaces_and_punctuation():
    result = apply_strict("Текст ,следом", provider=MockProvider([]))
    assert result == "Текст, следом"


def test_strict_cleans_brackets_quotes_and_repeats():
    result = apply_strict("( текст ) « привет » !!! ??? ,, ...", provider=MockProvider([]))
    assert "(текст)" in result
    assert "«привет»" in result
    assert "!" in result
    assert "?" in result
    assert "," in result
    assert "…" in result


def test_typo_legal_typography_present():
    assert "ст.\u00a015" in apply_typo("ст. 15 ГК РФ")


def test_typo_does_not_call_provider():
    provider = _CountProvider()
    engine = CorrectionEngine(provider=provider)
    engine.correct("Текст", mode="typo")
    assert provider.calls == 0


def test_typo_quotes_and_safe_dash():
    result = apply_typo('"тест" Москва - Петербург')
    assert "«тест»" in result
    assert "Москва — Петербург" in result


def test_engine_returns_correction_result_for_legal_mode_string():
    engine = CorrectionEngine(provider=MockProvider([]))
    result = engine.correct("ст. 15", mode="legal")
    assert isinstance(result, CorrectionResult)


def test_engine_unknown_mode_falls_back_to_legal():
    engine = CorrectionEngine(provider=MockProvider([]))
    result = engine.correct("ст. 15", mode="unknown-mode")
    assert "ст.\u00a015" in result.text


def test_legal_claim_full_text_normalization():
    src = (
        "прошу расторгнуть договор купли продажи недвижимости от 18.09.2023 "
        "поскольку продавец не сообщил о наличии обременений и ограничений в использовании объекта, "
        "а также предоставил недостоверные сведения о техническом состоянии квартиры прошу взыскать "
        "уплаченную сумму 3200000 руб. и проценты за пользование денежными средствами 15700 руб 25 коп. "
        "прошу рассмотреть настоящую претензию в течение 15 дней, а в случаи неудовлетворения требований "
        "буду вынуждены обращаться в суд в соответствии со ст 12 и ст. 450 к рф."
    )
    expected = (
        "Прошу расторгнуть договор купли-продажи недвижимости от 18 сентября 2023 года, "
        "поскольку продавец не сообщил о наличии обременений и ограничений в использовании объекта, "
        "а также предоставил недостоверные сведения о техническом состоянии квартиры. "
        "Прошу взыскать уплаченную сумму в размере 3 200 000 (Три миллиона двести тысяч) рублей и проценты за "
        "пользование денежными средствами в размере 15 700 (Пятнадцать тысяч семьсот) рублей 25 (Двадцать пять) копеек. "
        "Прошу рассмотреть настоящую претензию в течение 15 (Пятнадцать) дней, а в случае неудовлетворения "
        "требований буду вынужден обращаться в суд в соответствии со ст. 12 и ст. 450 ГК РФ."
    )
    result = apply_legal(src, provider=MockProvider([]))
    assert result.replace("\u00a0", " ") == expected


def test_legal_inject_v_razmere_for_amount():
    src = "прошу взыскать уплаченную сумму 3200000 руб"
    expected = "Прошу взыскать уплаченную сумму в размере 3 200 000 (Три миллиона двести тысяч) рублей"
    result = apply_legal(src, provider=MockProvider([]))
    assert result == expected


def test_legal_sentence_split_and_linkers_full_text():
    src = (
        "истец понес убытки в размере 15700 руб которые подлежат взысканию кроме того "
        "при заключении договора ответчик скрыл существенные обстоятельства отдельно обращаю внимание "
        "что претензия была направлена в срок не превышающий 10 дней в связи с чем считаю требования "
        "обоснованными и буду вынуждены обратиться в суд"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Кроме того," in result
    assert "Отдельно обращаю внимание," in result
    assert ". Кроме того," in result
    assert ". Отдельно обращаю внимание," in result
    assert "буду вынуждены" not in result
    assert "буду вынужден обратиться" in result


def test_legal_regression_k_rome_marker_split():
    src = (
        "прошу взыскать штраф в размере 5000 руб за отказ в добровольном удовлетворении требований "
        "кроме того мной были понесены расходы на оплату услуг юриста в размере 15000 руб которые "
        "также подлежат взысканию"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "к. роме" not in result
    assert "требований. Кроме того," in result
    assert "15 000" in result
    assert "рублей, которые" in result


def test_legal_regression_krome_togo_stable_replacement():
    src = "требований кроме того мной были расходы"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "к. роме" not in result
    assert "Требований. Кроме того, мной были расходы" in result


def test_legal_v_razmere_for_percents_with_kopeks():
    src = "проценты за пользование денежными средствами 18300 руб 50 коп"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert (
        "Проценты за пользование денежными средствами в размере "
        "18 300 (Восемнадцать тысяч триста) рублей 50 (Пятьдесят) копеек"
    ) in result
    assert "в размере в размере" not in result


def test_legal_punctuation_causal():
    src = "договор подлежит расторжению так как обязательства не исполнены"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Договор подлежит расторжению, так как обязательства не исполнены" in result


def test_legal_punctuation_conditional():
    src = "обращусь в суд если требования не будут удовлетворены"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Обращусь в суд, если требования не будут удовлетворены" in result


def test_legal_punctuation_v_sluchae_keep():
    src = "в случае неудовлетворения требований буду вынужден обратиться в суд"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "В случае неудовлетворения требований буду вынужден обратиться в суд" in result
    assert "в случае, неудовлетворения" not in result


def test_legal_punctuation_target():
    src = "прошу предоставить документы чтобы подтвердить исполнение обязательств"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Прошу предоставить документы, чтобы подтвердить исполнение обязательств" in result


def test_legal_punctuation_krome_togo_sentence():
    src = "требования нарушены кроме того понесены расходы"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Требования нарушены. Кроме того, понесены расходы" in result


def test_legal_punctuation_a_takzhe():
    src = "продавец не сообщил об обременениях а также предоставил недостоверные сведения"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Продавец не сообщил об обременениях, а также предоставил недостоверные сведения" in result


def test_legal_punctuation_ukazannomu():
    src = "ответ должен быть направлен по адресу регистрации указанному в договоре"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "по адресу регистрации, указанному в договоре" in result


def test_legal_punctuation_v_svyazi_s_chem():
    src = "обязательства нарушены в связи с чем договор подлежит расторжению"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Обязательства нарушены, в связи с чем договор подлежит расторжению" in result


def test_legal_punctuation_stress_text():
    src = (
        "прошу расторгнуть договор купли продажи от 05.01.2022 так как продавец не сообщил об обременениях "
        "а также предоставил недостоверные сведения кроме того прошу взыскать сумму 2450000 руб за отказ "
        "в добровольном порядке и проценты за пользование денежными средствами 18300 руб 50 коп которые "
        "а также расходы 15000 руб которые "
        "подлежат взысканию в связи с чем считаю требования обоснованными прошу рассмотреть претензию в течение "
        "10 дней в случае неудовлетворения требований буду вынужден обратиться в суд в соответствии со ст 10 и "
        "ст. 450 к рф отдельно обращаю внимание что корреспонденция направлялась по адресу проживания указанному "
        "в договоре"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")

    assert "от 5 января 2022 года" in result
    assert ", а также" in result
    assert ". Кроме того," in result
    assert ", в связи с чем" in result
    assert "денежными средствами в размере" in result
    assert ". В случае неудовлетворения" in result
    assert "ст. 10" in result
    assert "ст. 450 ГК РФ" in result
    assert "рублей за отказ" in result
    assert "рублей, которые" in result
    assert "Отдельно обращаю внимание," in result
    assert "проживания, указанному" in result
    assert result.endswith(".")

    assert "к. роме" not in result
    assert ", ," not in result
    assert "рублей. за" not in result
    assert "рублей. которые" not in result
    assert "в размере в размере" not in result


def test_legal_punctuation_fix_ya_comma():
    src = "Я заключил договор"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert result == "Я, заключил договор."


def test_legal_punctuation_fix_semicolon_odnako():
    src = "условия согласованы; однако исполнитель не исполнил обязательства"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "условия согласованы, однако исполнитель не исполнил обязательства" in result.lower()
    assert "; однако" not in result.lower()


def test_legal_safe_subordinate_punctuation():
    src = (
        "пользователь столкнулся с утечкой персональных данных так как компания "
        "не обеспечила защиту информации вследствие чего данные могли быть "
        "использованы третьими лицами что создает риски"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "данных, так как" in result
    assert "информации, вследствие чего" in result
    assert "лицами, что" in result
    assert "создаёт риски" in result


def test_legal_safe_iz_za():
    src = "команда допустила ошибки из за которых система работала нестабильно"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "ошибки, из-за которых" in result


def test_legal_safe_krome_togo_v_chastnosti():
    src = "система работала нестабильно в частности возникали ошибки кроме того интерфейс был неудобным"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert ". В частности," in result
    assert ". Кроме того," in result


def test_legal_v_razmere_lawyer_expenses():
    src = "мной были понесены расходы на оплату услуг юриста 18000 руб которые также подлежат взысканию"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert (
        "расходы на оплату услуг юриста в размере 18 000 (Восемнадцать тысяч) рублей, "
        "которые также подлежат взысканию"
    ) in result


def test_legal_v_razmere_neustoyka():
    src = "прошу взыскать неустойку 7000 руб за нарушение прав потребителя"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "неустойку в размере 7 000 (Семь тысяч) рублей за нарушение прав потребителя" in result


def test_legal_v_razmere_sudebnye_rashody():
    src = "прошу взыскать судебные расходы 35000 руб"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "судебные расходы в размере 35 000 (Тридцать пять тысяч) рублей" in result


def test_legal_v_razmere_moral_harm():
    src = "прошу взыскать компенсацию морального вреда 50000 руб"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "компенсацию морального вреда в размере 50 000 (Пятьдесят тысяч) рублей" in result


def test_legal_v_razmere_no_duplicate():
    src = "прошу взыскать неустойку в размере 7000 руб"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "в размере в размере" not in result


def test_legal_money_marker_normalizer_unit():
    assert legal_rules._normalize_money_markers("200000 р. 50 коп.") == "200000 руб 50 коп"
    assert legal_rules._normalize_money_markers("200000 руб.") == "200000 руб"


def test_legal_money_context_inference_unit():
    assert (
        legal_rules._infer_money_amounts_from_context("денежные средства 120000 были перечислены")
        == "денежные средства 120000 руб были перечислены"
    )
    assert (
        legal_rules._infer_money_amounts_from_context(
            "процентов за пользование чужими денежными средствами 120000 75 коп"
        )
        == "процентов за пользование чужими денежными средствами 120000 руб 75 коп"
    )
    assert legal_rules._infer_money_amounts_from_context("в срок 5 дней") == "в срок 5 дней"


def test_legal_money_pipeline_stage_order_for_verb_context():
    src = "прошу взыскать задолженность 120000р 75 коп"
    stage_1 = legal_rules._normalize_money_markers(src)
    assert "120000 руб 75 коп" in stage_1
    stage_2 = legal_rules._infer_money_amounts_from_context(stage_1)
    assert stage_2.count("120000 руб 75 коп") == 1
    assert (
        normalize_money(src)
        == "прошу взыскать задолженность 120 000 (Сто двадцать тысяч) рублей 75 (Семьдесят пять) копеек"
    )


def test_legal_bare_money_amounts_from_context_cases():
    cases = [
        (
            "денежные средства 120000 были перечислены",
            "Денежные средства в размере 120 000 (Сто двадцать тысяч) рублей были перечислены.",
        ),
        (
            "с иском о взыскании денежных средств 120000",
            "С иском о взыскании денежных средств в размере 120 000 (Сто двадцать тысяч) рублей",
        ),
        (
            "процентов за пользование чужими денежными средствами 120000 75 коп",
            "Процентов за пользование чужими денежными средствами в размере "
            "120 000 (Сто двадцать тысяч) рублей 75 (Семьдесят пять) копеек",
        ),
        (
            "компенсацию морального вреда 30000",
            "Компенсацию морального вреда в размере 30 000 (Тридцать тысяч) рублей",
        ),
        (
            "расходы на оплату услуг представителя 40000",
            "Расходы на оплату услуг представителя в размере 40 000 (Сорок тысяч) рублей",
        ),
        ("ст 10 гк рф", "ст. 10 ГК РФ"),
        ("договор № B55-77/2023", "Договор № B55-77/2023"),
        ("01.02.2023 г", "1 февраля 2023 года"),
        (
            "200000 р 50 коп",
            "200 000 (Двести тысяч) рублей 50 (Пятьдесят) копеек",
        ),
    ]

    for src, expected_fragment in cases:
        result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
        assert expected_fragment in result
        assert "в размере в размере" not in result

    days_result = apply_legal("в срок 5 дней", provider=MockProvider([])).replace("\u00a0", " ")
    assert "В срок 5 (Пять) дней." == days_result
    assert "руб" not in days_result


def test_legal_ap_14_2024_money_and_punctuation_regression():
    src = (
        "Я 10 марта 2024 года заключил с исполнителем договор на подготовку апелляционной жалобы и "
        "представление интересов в суде; однако исполнитель свои обязательства не выполнил, так как жалоба "
        "в суд подана не была, сроки обжалования были пропущены, а каких-либо доказательств работы мне не "
        "предоставили.\n\n"
        "Исполнитель сообщил, что документы уже готовы и якобы переданы юристу для подачи, но копию жалобы, "
        "квитанцию об отправке и подтверждение направления документов в суд мне не направил.\n\n"
        "За услуги мной была оплачена сумма 85 000 (Восемьдесят пять тысяч) рублей; однако фактически никакого "
        "результата оказания услуг я не получил и в последующем был вынужден обратиться к другому представителю, "
        "оплатив дополнительно 45000.\n\n"
        "Считаю, что действия исполнителя нарушают ст. 309 ГК РФ, ст. 310 ГК РФ и ст. 15 ГК РФ, поскольку "
        "обязательства должны исполняться надлежащим образом, а, причиненные мне убытки подлежат возмещению "
        "в полном объёме.\n\n"
        "В случае, если требования не будут удовлетворены добровольно, я буду вынужден обратиться в суд с иском "
        "о взыскании уплаченных денежных средств в размере 85 000 (Восемьдесят пять тысяч) рублей, а также "
        "убытков 45000 и процентов за пользование чужими денежными средствами в размере 85 000 "
        "(Восемьдесят пять тысяч) рублей 35 (Тридцать пять) копеек за период с 10 марта 2024 года по "
        "10 мая 2024 года.\n\n"
        "Кроме того, прошу компенсировать моральный вред 60000, поскольку из-за бездействия исполнителя я "
        "лишился возможности своевременно обжаловать судебный акт и понёс дополнительные расходы.\n\n"
        "Прошу вернуть денежные средства в размере 85 000 (Восемьдесят пять тысяч) рублей, возместить убытки "
        "в размере 45 000 (Сорок пять тысяч) рублей и направить письменный ответ по адресу, указанному в "
        "договоре, в срок 7 (семь) дней с момента получения настоящей претензии.\n\n"
        "Договор № AP-14/2024 был заключен 10 марта 2024 года; оплата подтверждается платежным поручением; "
        "однако исполнитель до настоящего времени не предоставил отчётность и не сообщил, какие именно "
        "действия были выполнены."
    )

    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")

    expected_fragments = [
        "сумма в размере 85 000 (Восемьдесят пять тысяч) рублей",
        "оплатив дополнительно 45 000 (Сорок пять тысяч) рублей",
        "убытков в размере 45 000 (Сорок пять тысяч) рублей",
        "компенсировать моральный вред в размере 60 000 (Шестьдесят тысяч) рублей",
        "денежными средствами в размере 85 000 (Восемьдесят пять тысяч) рублей "
        "35 (Тридцать пять) копеек",
        "Договор № AP-14/2024",
        "ст. 309 ГК РФ",
        "10 марта 2024 года",
        "7 (семь) дней",
    ]
    for fragment in expected_fragments:
        assert fragment in result

    forbidden_fragments = [
        "а, причиненные",
        "а, причинённые",
        "в размере в размере",
        ", ,",
        "что. В",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in result


def test_legal_stress_big_text_extended():
    src = (
        "прошу расторгнуть договор купли продажи от 03.02.2023 так как ответчик не предоставил информацию "
        "а также исказил сведения кроме того прошу взыскать денежные средства 3150000 руб и проценты за "
        "пользование денежными средствами 21450 руб 50 коп и неустойку 7000 руб и расходы на оплату услуг "
        "юриста 18000 руб которые подлежат взысканию в связи с чем считаю требования обоснованными прошу "
        "рассмотреть претензию в течение 10 дней в случае неудовлетворения требований буду вынужден обратиться "
        "в суд в соответствии со ст 10 и ст. 450 к рф отдельно обращаю внимание что документы направлены по "
        "адресу проживания указанному в договоре"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")

    assert "от 3 февраля 2023 года" in result
    assert ", так как" in result
    assert ". Кроме того," in result
    assert ", в связи с чем" in result
    assert "денежные средства в размере 3 150 000" in result
    assert "денежными средствами в размере 21 450" in result
    assert "неустойку в размере 7 000" in result
    assert "расходы на оплату услуг юриста в размере 18 000" in result
    assert "рублей, которые" in result
    assert "Отдельно обращаю внимание," in result
    assert "проживания, указанному" in result
    assert result.endswith(".")

    assert "к. роме" not in result
    assert ", ," not in result
    assert "рублей. за" not in result
    assert "рублей. которые" not in result
    assert "в размере в размере" not in result
    assert "из за" not in result


def test_legal_no_p_rosheu_artifact():
    src = "прошу предоставить документы"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "п. рошу" not in result


def test_legal_no_v_sledstvie_artifact():
    src = "вследствие этого данные могли быть использованы"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "в. следствие" not in result
    assert "Вследствие этого" in result


def test_legal_dotless_refs_still_work():
    src = "п 2.1 договора ст 15 гк рф"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "п. 2.1" in result
    assert "ст. 15" in result
    assert "ГК РФ" in result


def test_legal_v_svyazi_s_tem_chto_and_date_proshu_split():
    src = (
        "в связи с тем что ваша компания не ответила на обращение направленное 12.04.2024 "
        "прошу предоставить информацию"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "В связи с тем, что" in result
    assert "12 апреля 2024 года. Прошу предоставить" in result


def test_legal_multiline_large_text_no_artifacts():
    src = (
        "прошу взыскать штраф в размере 5000 руб за отказ в добровольном удовлетворении требований\n\n"
        "кроме того мной были понесены расходы на оплату услуг юриста в размере 15000 руб которые также подлежат взысканию\n\n"
        "вследствие этого прошу учесть обстоятельства в связи с тем что ответ не был предоставлен"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "п. рошу" not in result
    assert "в. следствие" not in result
    assert "к. роме" not in result
    assert ", ," not in result


def test_legal_no_i_dot_pri_etom_artifact():
    src = "и. При этом требования остаются"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "и. При этом" not in result


def test_legal_stable_no_dot_after_single_conjunction_i():
    src = "исполнитель не исполнил обязательства в полном объеме и при этом ввел меня в заблуждение"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "и. При этом" not in result
    assert "в полном объёме и при этом ввёл" in result


def test_legal_split_before_krome_togo_marker():
    src = "условий сделки кроме того часть услуг не была оказана"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Условий сделки. Кроме того, часть услуг" in result


def test_legal_comma_not_dot_before_v_svyazi_s_chem():
    src = "заявленным требованиям в связи с чем считаю необходимым расторгнуть договор"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Заявленным требованиям, в связи с чем считаю" in result


def test_legal_special_days_v_sluchae_split():
    src = "прошу рассмотреть заявление в срок не превышающий 10 дней в случае неудовлетворения требований буду вынужден обратиться"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "10 (Десять) дней. В случае неудовлетворения требований буду вынужден обратиться" in result


def test_legal_inner_punctuation_no_artifacts_for_but_and_chto():
    src = "вчера я пришел в магазин чтобы купить продукты но оказалось что товары были просрочены"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "пришёл в магазин, чтобы купить продукты, но оказалось, что товары" in result


def test_legal_sentence_split_after_date_before_proshu():
    src = "ответила на мое обращение направленное 12.04.2024 прошу предоставить информацию"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "обращение, направленное 12 апреля 2024 года. Прошу предоставить" in result


def test_legal_sentence_split_dopolnitelno_and_v_protivnom():
    src = "ответа дополнительно прошу указать сроки исполнения обязательств в противном случае буду вынужден"
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "Ответа. Дополнительно прошу" in result
    assert "обязательств. В противном случае" in result


def test_legal_stress_text_no_new_artifacts_and_required_markers():
    src = (
        "прошу расторгнуть договор купли продажи от 03.02.2023 так как ответчик не предоставил информацию "
        "и при этом ввел в заблуждение относительно качества товара кроме того прошу взыскать денежные средства "
        "3150000 руб в связи с чем считаю требования обоснованными прошу рассмотреть претензию в срок не "
        "превышающий 10 дней в случае неудовлетворения требований дополнительно прошу указать сроки исполнения "
        "обязательств в противном случае буду вынужден обратиться в суд вследствие этого прошу принять меры"
    )
    result = apply_legal(src, provider=MockProvider([])).replace("\u00a0", " ")
    assert "и. При этом" not in result
    assert "п. рошу" not in result
    assert "в. следствие" not in result
    assert "к. роме" not in result
    assert ", ," not in result
    assert " ." not in result
    assert ". Кроме того," in result
    assert ", в связи с чем" in result
    assert ". В случае неудовлетворения" in result
    assert ". Дополнительно прошу" in result
    assert ". В противном случае" in result
    assert ". Вследствие этого" in result


def test_legal_real_telegram_stress_text_contract():
    src = (
        "прошу признать договор оказания услуг от 03.02.2023 недействительным так как исполнитель не исполнил "
        "обязательства в полном объеме и при этом ввел меня в заблуждение относительно реальных условий сделки "
        "кроме того часть услуг фактически не была оказана а результаты предоставленных работ не соответствуют "
        "заявленным требованиям в связи с чем считаю необходимым расторгнуть договор и вернуть уплаченные денежные "
        "средства 3150000 руб а также проценты за пользование денежными средствами 21450 руб 30 коп прошу "
        "рассмотреть настоящее заявление в срок не превышающий 10 дней в случаи неудовлетворения требований буду "
        "вынуждены обратиться в суд в соответствии со ст 15 и ст 450 гк рф а также прошу взыскать неустойку "
        "7000 руб за нарушение прав потребителя кроме того мной были понесены расходы на оплату услуг юриста "
        "18000 руб которые также подлежат взысканию отдельно обращаю внимание что ответ должен быть направлен "
        "на электронную почту либо по адресу проживания указанному в договоре\n\n"
        "вчера я пришел в магазин чтобы купить продукты но оказалось что многие товары были просрочены и продавец "
        "отказался вернуть деньги ссылаясь на внутренние правила хотя по закону он обязан это сделать кроме того "
        "на кассе неправильно посчитали сумму покупки и включили в чек товары которые я не приобретал в результате "
        "мне пришлось потратить время на разбирательство и писать жалобу в администрацию магазина после чего мне "
        "вернули только часть средств\n\n"
        "в связи с тем что ваша компания не ответила на мое обращение направленное 12.04.2024 прошу предоставить "
        "информацию о текущем статусе рассмотрения а также разъяснить причины задержки ответа дополнительно прошу "
        "указать конкретные сроки исполнения обязательств в противном случае буду вынужден обратиться в контролирующие "
        "органы и инициировать проверку деятельности организации\n\n"
        "при разработке программного обеспечения команда допустила ряд ошибок из за которых система начала работать "
        "нестабильно в частности возникали проблемы с подключением к серверу а также происходила потеря данных при "
        "одновременном доступе нескольких пользователей кроме того интерфейс приложения оказался неудобным и "
        "пользователи не могли быстро найти нужные функции что привело к снижению эффективности работы сотрудников\n\n"
        "при использовании интернет сервиса пользователь столкнулся с утечкой персональных данных так как компания "
        "не обеспечила должный уровень защиты информации вследствие этого данные могли быть использованы третьими "
        "лицами что создает риски для безопасности пользователя и требует принятия мер по устранению последствий"
    )
    result = CorrectionEngine(provider=_TelegramLikeBrokenProvider()).correct(src, mode="legal").text.replace("\u00a0", " ")

    expected_fragments = [
        "недействительным, так как",
        "в полном объёме и при этом",
        "условий сделки. Кроме того,",
        "требованиям, в связи с чем",
        "копеек. Прошу рассмотреть",
        "10 (Десять) дней. В случае неудовлетворения",
        "купить продукты, но оказалось, что",
        "деньги, ссылаясь на",
        "правила, хотя",
        "товары, которые",
        "обращение, направленное 12 апреля 2024 года. Прошу",
        "ответа. Дополнительно прошу",
        "обязательств. В противном случае",
        "ошибок, из-за которых",
        "информации. Вследствие этого",
    ]
    for fragment in expected_fragments:
        assert fragment in result

    forbidden_fragments = [
        "и. При этом",
        "п. рошу",
        "в. следствие",
        "к. роме",
        ", ,",
        " .",
        "рублей. за",
        "рублей. которые",
        "к рф",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in result


def test_legal_stress_full_document_expected_output():
    assert 4000 <= len(LEGAL_STRESS_RAW) <= 7000
    assert LEGAL_STRESS_EXPECTED

    result = apply_legal(LEGAL_STRESS_RAW, provider=MockProvider([])).replace("\u00a0", " ")
    paragraphs = [paragraph for paragraph in result.split("\n\n") if paragraph.strip()]

    # Причинные союзы: так как, потому что, поскольку, вследствие чего.
    # Правило: перед придаточным союзом ставится запятая, если он соединяет части сложного предложения.
    # Целевые союзы: чтобы, для того чтобы. Правило: перед придаточным цели ставится запятая.
    # Условные конструкции: если, в случае если. Правило: перед придаточным условия ставится запятая;
    # конструкция "в случае неудовлетворения требований" не требует запятой после "случае".
    # Вводные/присоединительные: кроме того, в частности, таким образом, следовательно, вместе с тем.
    # Правило: конструкция выделяется запятой; если начинается новый смысловой блок — ставится точка.
    # Относительные слова: который, которая, которые, указанному, направленное.
    # Правило: придаточная часть или причастный оборот после определяемого слова обособляется.
    # Деепричастные обороты: ссылаясь на, учитывая, принимая во внимание. Правило: оборот обособляется.
    # Юридические ссылки: ст 15, ст 450 гк рф, п 2.1, ч 3 ст 15 приводятся к сокращениям с точкой.
    # Суммы: legal-режим ставит пробелы в числах и добавляет пропись в скобках.
    # "В размере": добавляется перед суммой после юридически подходящих денежных контекстов.
    # Даты: 03.02.2023 приводится к текстовому формату. Финальная точка добавляется при необходимости.
    expected_fragments = [
        ", так как",
        ". Кроме того,",
        ", в связи с чем",
        ". Дополнительно прошу",
        ". В противном случае",
        ". Вследствие этого",
        ". Вместе с тем,",
        "терапии, потому что",
        "сотрудников, учитывая",
        "объёме, принимая во внимание",
        "сообщить, какие меры",
        "не сообщил, какие именно сведения",
        "исполнителем, когда",
        "Таким образом, прошу",
        "денежные средства в размере",
        "проценты за пользование денежными средствами в размере",
        "неустойку в размере",
        "расходы на оплату услуг юриста в размере",
        "ст. 15",
        "ст. 450 ГК РФ",
        "п. 2.1",
        "ч. 3 ст. 15. Прошу вернуть",
        "по адресу проживания, указанному",
        "интернет-сервиса",
        "отчётности",
        "создаёт",
        "в полном объёме",
        "3 150 000 (Три миллиона сто пятьдесят тысяч) рублей",
        "21 450 (Двадцать одна тысяча четыреста пятьдесят) рублей 30 (Тридцать) копеек",
        "12 апреля 2024 года",
        "15 августа 2022 года",
        ". Прошу",
        "Вчера",
        "При разработке",
        "В медицинском учреждении",
    ]
    for fragment in expected_fragments:
        assert fragment in result

    forbidden_fragments = [
        "п. рошу",
        "в. следствие",
        "к. роме",
        "и. При этом",
        ", ,",
        "рублей. за",
        "рублей. которые",
        "в размере в размере",
        "из за",
        "гк рф",
        "в случаи",
        "потому, что",
        "Таким образом. Прошу",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in result

    for paragraph in paragraphs:
        first = next(char for char in paragraph if char.isalpha())
        assert first == first.upper()

    assert result.endswith(".")
