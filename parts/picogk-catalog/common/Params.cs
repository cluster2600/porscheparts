using System.Text.Json;
using System.Text.Json.Serialization;

namespace PicoGKCatalog;

/// One numeric input with its provenance. basis is one of:
///   published  - read on a cited manufacturer/retailer page or manual;
///   catalogue  - taken from a repository catalogue record (which cites its source);
///   community  - forum or owner measurement, cited;
///   assumption - chosen for the concept; NOT evidence, blocks any fit claim.
public sealed record Param(
    [property: JsonPropertyName("value")] double Value,
    [property: JsonPropertyName("unit")] string Unit,
    [property: JsonPropertyName("basis")] string Basis,
    [property: JsonPropertyName("source")] string? Source,
    [property: JsonPropertyName("note")] string? Note);

public sealed class PartSpec
{
    [JsonPropertyName("part_id")] public string PartId { get; set; } = "";
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("generator")] public string Generator { get; set; } = "";
    [JsonPropertyName("catalogue_record")] public string? CatalogueRecord { get; set; }
    [JsonPropertyName("porsche_part_numbers")] public List<string> PorschePartNumbers { get; set; } = new();
    [JsonPropertyName("safety_class")] public string SafetyClass { get; set; } = "";
    [JsonPropertyName("material_candidate")] public string MaterialCandidate { get; set; } = "";
    [JsonPropertyName("density_g_cm3")] public double DensityGCm3 { get; set; }
    [JsonPropertyName("voxel_mm")] public float VoxelMm { get; set; } = 0.3f;
    [JsonPropertyName("picogk_enhancement")] public string PicogkEnhancement { get; set; } = "";
    [JsonPropertyName("parameters")] public Dictionary<string, Param> Parameters { get; set; } = new();
    [JsonPropertyName("open_interfaces")] public List<string> OpenInterfaces { get; set; } = new();
    [JsonPropertyName("status")] public string Status { get; set; } = "";

    public float P(string name) =>
        Parameters.TryGetValue(name, out Param? p)
            ? (float)p.Value
            : throw new KeyNotFoundException($"{PartId}: missing parameter '{name}'");

    public int N(string name) => (int)Math.Round(P(name));

    public static PartSpec Load(string path) =>
        JsonSerializer.Deserialize<PartSpec>(File.ReadAllText(path))
        ?? throw new InvalidDataException($"cannot parse {path}");
}
