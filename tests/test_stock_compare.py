from app.services.meta_ai import (
    _extract_json,
    base_item_name,
    compare_stock,
    parse_packaging_spec,
    spec_from_item_name,
)

class TestBaseItemName:
    def test_strips_packaging_spec(self):
        assert base_item_name("Rice (50kg)") == "rice"

    def test_lowercases_and_trims(self):
        assert base_item_name("  Beans  ") == "beans"

    def test_handles_nested_parens(self):
        assert base_item_name("Rice (50kg bags)") == "rice"

class TestPackagingSpec:
    def test_reads_label_text(self):
        assert parse_packaging_spec("25 Kgs Net") == "25kg"

    def test_reads_spaced_unit(self):
        assert parse_packaging_spec("50 kg") == "50kg"

    def test_reads_volume(self):
        assert parse_packaging_spec("500ml bottle") == "500ml"

    def test_no_size_is_blank(self):
        assert parse_packaging_spec("Rice") == ""

    def test_spec_out_of_item_name(self):
        assert spec_from_item_name("Rice (25kg)") == "25kg"

    def test_item_without_spec(self):
        assert spec_from_item_name("Rice") == ""

class TestCompareStock:
    def test_exact_match_is_consistent(self):
        result = compare_stock([{"item": "Rice", "count": 3}], ["Rice"], [3])
        assert result["verdict"] == "consistent"

    def test_ledger_packaging_spec_still_matches(self):
        """The bug that broke real uploads: ledger says 'Rice (50kg)', model says 'Rice'."""
        result = compare_stock([{"item": "Rice", "count": 3}], ["Rice (50kg)"], [3])
        assert result["verdict"] == "consistent"

    def test_detected_packaging_spec_still_matches(self):
        result = compare_stock([{"item": "Rice (50kg)", "count": 3}], ["Rice"], [3])
        assert result["verdict"] == "consistent"

    def test_variants_are_summed(self):
        detected = [{"item": "Rice (50kg)", "count": 2}, {"item": "Rice (25kg)", "count": 1}]
        result = compare_stock(detected, ["Rice"], [3])
        assert result["verdict"] == "consistent"

    def test_shortfall_triggers_review(self):
        result = compare_stock([{"item": "Rice", "count": 2}], ["Rice"], [3])
        assert result["verdict"] == "review"
        assert result["short"] == ["Rice"]

    def test_extra_stock_is_not_a_shortfall(self):
        result = compare_stock([{"item": "Rice", "count": 10}], ["Rice"], [3])
        assert result["verdict"] == "consistent"

    def test_nothing_detected_is_unknown(self):
        result = compare_stock([], ["Rice"], [3])
        assert result["verdict"] == "unknown"

    def test_unrelated_product_does_not_satisfy_quantity(self):
        result = compare_stock([{"item": "Beans", "count": 5}], ["Rice"], [1])
        assert result["verdict"] == "review"

    def test_missing_quantity_defaults_to_zero(self):
        result = compare_stock([{"item": "Rice", "count": 1}], ["Rice", "Beans"], [1])
        assert result["verdict"] == "consistent"

    def test_blank_item_names_are_ignored(self):
        detected = [{"item": "", "count": 9}, {"item": "Rice", "count": 3}]
        result = compare_stock(detected, ["Rice"], [3])
        assert result["verdict"] == "consistent"

    def test_packaging_size_mismatch_triggers_review(self):
        """3 × 25kg recorded, but the shelf holds 50kg bags — counts agree, sizes don't."""
        detected = [{"item": "Rice", "count": 3, "spec": "50 Kgs Net"}]
        result = compare_stock(detected, ["Rice (25kg)"], [3])
        assert result["verdict"] == "review"
        assert result["short"] == []
        assert result["packaging"] == ["Rice (25kg)"]
        assert "packaging size" in result["message"]

    def test_matching_packaging_size_is_consistent(self):
        detected = [{"item": "Rice", "count": 3, "spec": "25 Kgs Net"}]
        result = compare_stock(detected, ["Rice (25kg)"], [3])
        assert result["verdict"] == "consistent"

    def test_unreadable_size_is_never_flagged(self):
        """No spec seen in the photo means no size claim can be made."""
        result = compare_stock([{"item": "Rice", "count": 3}], ["Rice (25kg)"], [3])
        assert result["verdict"] == "consistent"

    def test_shortfall_outranks_packaging(self):
        detected = [{"item": "Rice", "count": 2, "spec": "50kg"}]
        result = compare_stock(detected, ["Rice (25kg)"], [3])
        assert result["verdict"] == "review"
        assert result["short"] == ["Rice (25kg)"]

    def test_checks_carry_one_row_per_recorded_item(self):
        detected = [{"item": "Rice", "count": 3, "spec": "50 Kgs Net"}]
        result = compare_stock(detected, ["Rice (25kg)", "Beans"], [3, 0])

        assert [row["item"] for row in result["checks"]] == ["Rice (25kg)", "Beans"]
        first = result["checks"][0]
        assert first["status"] == "packaging"
        assert first["recorded"] == 3
        assert first["detected"] == 3
        assert first["recorded_spec"] == "25kg"
        assert first["seen_spec"] == "50kg"
        assert result["checks"][1]["status"] == "match"

    def test_short_row_reports_short_status(self):
        result = compare_stock([{"item": "Rice", "count": 2}], ["Rice"], [3])
        assert result["checks"][0]["status"] == "short"

class TestExtractJson:
    def test_plain_object(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fence(self):
        assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_surrounding_prose(self):
        assert _extract_json('Here you go:\n{"a": 1}\nDone.') == {"a": 1}
