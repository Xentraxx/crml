from crml_lang import validate_control_catalog


def test_validate_control_catalog_pack_valid() -> None:
    yaml_text = """
crml_control_catalog: "1.0"
meta:
  name: "cisv8-catalog"
catalog:
  id: "cisv8-ids"
  framework: "CIS v8"
  controls:
    - id: "cisv8:4.2"
      title: "Secure configuration of enterprise assets"
      url: "https://www.cisecurity.org/controls"
      tags: ["configuration", "hardening"]
    - id: "cisv8:5.1"
      title: "Account management"
      tags: ["identity"]
"""

    report = validate_control_catalog(yaml_text, source_kind="yaml")
    assert report.ok, report.render_text(source_label="inline")


def test_validate_control_catalog_pack_rejects_duplicate_ids() -> None:
    yaml_text = """
crml_control_catalog: "1.0"
meta:
  name: "duplicate-catalog"
catalog:
  framework: "CIS v8"
  controls:
    - id: "cisv8:4.2"
    - id: "cisv8:4.2"
"""

    report = validate_control_catalog(yaml_text, source_kind="yaml")
    assert report.ok is False
    assert any("duplicate" in e.message.lower() for e in report.errors)
