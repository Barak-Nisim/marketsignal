from marketsignal.charts import sparkline_svg


def test_returns_empty_string_for_fewer_than_two_points():
    assert sparkline_svg([]) == ""
    assert sparkline_svg([1.0]) == ""
    assert sparkline_svg([None, 1.0]) == ""


def test_renders_an_svg_for_two_or_more_points():
    svg = sparkline_svg([1.0, 2.0, 1.5])

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert "<polyline" in svg
    assert svg.count(",") >= 3  # at least 3 coordinate pairs


def test_ignores_none_values_but_still_renders_with_enough_real_points():
    svg = sparkline_svg([1.0, None, 2.0, None, 3.0])

    assert svg.startswith("<svg")


def test_flat_series_does_not_divide_by_zero():
    svg = sparkline_svg([2.0, 2.0, 2.0])

    assert svg.startswith("<svg")


def test_custom_dimensions_and_color_are_applied():
    svg = sparkline_svg([1.0, 2.0], width=100, height=20, color="#ff0000")

    assert 'width="100"' in svg
    assert 'height="20"' in svg
    assert "#ff0000" in svg


def test_last_point_gets_a_marker_circle():
    svg = sparkline_svg([1.0, 2.0, 3.0])

    assert "<circle" in svg
