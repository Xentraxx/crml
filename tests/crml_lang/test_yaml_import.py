from crml_lang import CRModel, load_from_yaml, load_from_yaml_str


def test_load_from_yaml_path(valid_crml_file: str) -> None:
    model = CRModel.load_from_yaml(valid_crml_file)

    assert model.crml == "1.1"
    assert model.meta.name == "test-model"
    assert model.model.assets[0].cardinality == 100
    assert isinstance(model.model.assets[0].cardinality, int)


def test_load_from_yaml_str(valid_crml_content: str) -> None:
    model = CRModel.load_from_yaml_str(valid_crml_content)

    assert model.crml == "1.1"
    assert model.meta.name == "test-model"
    assert model.model.assets[0].cardinality == 100


def test_module_level_helpers_match_methods(valid_crml_file: str, valid_crml_content: str) -> None:
    m1 = load_from_yaml(valid_crml_file)
    m2 = CRModel.load_from_yaml(valid_crml_file)
    assert m1.model_dump() == m2.model_dump()

    s1 = load_from_yaml_str(valid_crml_content)
    s2 = CRModel.load_from_yaml_str(valid_crml_content)
    assert s1.model_dump() == s2.model_dump()
