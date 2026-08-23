from scripts.generate_apriltag_target import generate_svg, marker_modules


def test_printable_apriltag_target_is_deterministic_and_instructive() -> None:
    first = generate_svg(family="tag36h11", tag_id=7, nominal_tag_size_mm=120.0)
    second = generate_svg(family="tag36h11", tag_id=7, nominal_tag_size_mm=120.0)
    assert first == second
    assert "tag36h11 id 7" in first
    assert "Print at 100%" in first
    assert "100 mm scale reference" in first
    assert "measured value in PnP" in first
    modules = marker_modules("tag36h11", 7)
    assert modules.shape == (8, 8)
