from yen import some_function


def test_some_function() -> None:
    """Tests some_function from the package."""
    output = some_function()
    assert output == "This is a string"
