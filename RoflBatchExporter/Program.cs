using System.Text.Json;
using System.Text.Json.Serialization;
using Fraxiinus.Rofl.Extract.Data.Models;
using Fraxiinus.Rofl.Extract.Data.Models.Rofl;
using Fraxiinus.Rofl.Extract.Data.Readers;

class Program
{
    static async Task<int> Main(string[] args)
    {
        if (args.Length == 0 || args.Contains("--help") || args.Contains("-h"))
        {
            PrintUsage();
            return args.Length == 0 ? 1 : 0;
        }

        var inputDirectory = Path.GetFullPath(args[0]);
        var outputDirectory = args.Length > 1
            ? Path.GetFullPath(args[1])
            : Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "json_files"));
        var overwrite = args.Contains("--overwrite");

        if (!Directory.Exists(inputDirectory))
        {
            Console.Error.WriteLine($"Input directory not found: {inputDirectory}");
            return 1;
        }

        Directory.CreateDirectory(outputDirectory);
        var options = new ReplayReaderOptions { LoadPayload = false };
        var jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        };

        var imported = 0;
        var skipped = 0;

        foreach (var roflFile in Directory.GetFiles(inputDirectory, "*.rofl"))
        {
            var outputFilePath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(roflFile) + ".json");
            if (File.Exists(outputFilePath) && !overwrite)
            {
                skipped++;
                continue;
            }

            try
            {
                var payload = await ExtractMatchPayload(roflFile, options);
                await File.WriteAllTextAsync(outputFilePath, JsonSerializer.Serialize(payload, jsonOptions));
                Console.WriteLine($"Imported {Path.GetFileName(roflFile)} -> {Path.GetFileName(outputFilePath)}");
                imported++;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error processing {roflFile}: {ex.Message}");
            }
        }

        Console.WriteLine($"Imported {imported} replays, skipped {skipped} existing files");
        return 0;
    }

    static void PrintUsage()
    {
        Console.WriteLine("Usage: RoflBatchExporter <input-dir> [output-dir] [--overwrite]");
        Console.WriteLine();
        Console.WriteLine("  input-dir   Directory containing .rofl replay files");
        Console.WriteLine("  output-dir  Destination for match JSON (default: repo json_files/)");
        Console.WriteLine("  --overwrite Replace existing JSON files");
        Console.WriteLine();
        Console.WriteLine("Prefer scripts/import_replays.py when Python is available.");
    }

    static async Task<object> ExtractMatchPayload(string roflFile, ReplayReaderOptions options)
    {
        await using var stream = File.OpenRead(roflFile);
        var signature = new byte[6];
        await stream.ReadExactlyAsync(signature);

        if (signature.SequenceEqual(ROFL.Signature))
        {
            stream.Seek(0, SeekOrigin.Begin);
            var replay = await RoflReader.LoadAsync(stream, options);
            return BuildPayload(Path.GetFileNameWithoutExtension(roflFile), replay.Metadata!);
        }

        if (signature.SequenceEqual(ROFL2.Signature))
        {
            stream.Seek(0, SeekOrigin.Begin);
            var replay = await Rofl2Reader.LoadAsync(stream, options);
            return BuildPayload(Path.GetFileNameWithoutExtension(roflFile), replay.Metadata!);
        }

        throw new InvalidOperationException("Unsupported replay format");
    }

    static object BuildPayload(string matchId, Metadata metadata)
    {
        return new
        {
            matchId,
            gameDuration = metadata.GameLength,
            gameVersion = metadata.GameVersion,
            participants = metadata.PlayerStatistics,
        };
    }

    static object BuildPayload(string matchId, Fraxiinus.Rofl.Extract.Data.Models.Rofl2.Metadata2 metadata)
    {
        return new
        {
            matchId,
            gameDuration = metadata.GameLength,
            gameVersion = metadata.GameVersion,
            participants = metadata.PlayerStatistics,
        };
    }
}
