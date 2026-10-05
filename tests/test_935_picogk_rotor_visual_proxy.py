from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/935-horizontal-cooling-system-f0/source/picogk-rotor-visual-proxy/Program.cs"
PROJECT = SOURCE.with_name("ScanGuidedRotorProxy.csproj")


def test_proxy_is_private_pico_gk_geometry_with_no_declared_millimetre_scale():
    source = SOURCE.read_text()
    assert "using PicoGK;" in source
    assert "CreatePrivateDirectory(output);" in source
    assert "source-coordinate resolution, never mm" in source
    assert "scan_geometry_preserved = false" in source
    assert "manufacturing_authorized = false" in source
    assert "/Users/" not in source
    assert "work/935" not in source


def test_proxy_keeps_the_observed_ten_blade_topology_and_open_bore_check():
    source = SOURCE.read_text()
    assert "public const int BladeCount = 10;" in source
    assert "Expected inter-blade gap is closed" in source
    assert "Visual bore is closed" in source
    assert "new ScanGuidedRotorProxy(scan.OuterRadius, scan.CentreXY)" in source


def test_project_targets_the_pico_gk_runtime_and_requires_a_private_assembly():
    project = PROJECT.read_text()
    assert "<TargetFramework>net9.0</TargetFramework>" in project
    assert "$(PicoGKAssembly)" in project
    assert "Supply -p:PicoGKAssembly=/private/path/PicoGK.dll" in project
