import { NextResponse } from "next/server";
import { readFile, readdir } from "fs/promises";
import path from "path";
import yaml from "js-yaml";

async function listYamlFiles(dir: string, baseDir: string): Promise<string[]> {
    const entries = await readdir(dir, { withFileTypes: true });
    const results: string[] = [];

    for (const entry of entries) {
        // Ignore common noise
        if (entry.name.startsWith(".")) continue;
        if (entry.name === "node_modules") continue;

        const abs = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            results.push(...await listYamlFiles(abs, baseDir));
            continue;
        }

        const isYaml = entry.name.endsWith(".yaml") || entry.name.endsWith(".yml");
        if (!isYaml) continue;

        // Exclude FX config documents from the examples gallery
        if (entry.name.startsWith("fx-config")) continue;

        results.push(path.relative(baseDir, abs));
    }

    return results;
}

export async function GET() {
    try {
        // Path to examples directory (relative to project root)
        const examplesDir = path.join(process.cwd(), "..", "examples");

        const yamlFiles = await listYamlFiles(examplesDir, examplesDir);

        // Read and parse each example
        const examples = await Promise.all(
            yamlFiles.map(async (file) => {
                const filePath = path.join(examplesDir, file);
                const content = await readFile(filePath, "utf-8");

                try {
                    const parsed: any = yaml.load(content);

                    // According to schema, regions and countries are in meta.locale
                    const locale = parsed?.meta?.locale || {};
                    const regions: string[] = Array.isArray(locale.regions) ? locale.regions : [];
                    const countries: string[] = Array.isArray(locale.countries) ? locale.countries : (typeof locale.countries === "string" ? [locale.countries] : []);

                    const id = file.replace(/\.(yaml|yml)$/, "").replace(/[\\/]/g, "__");

                    return {
                        id,
                        filename: file,
                        name: parsed?.meta?.name || file,
                        description: parsed?.meta?.description || "No description available",
                        tags: parsed?.meta?.tags || [],
                        regions,
                        countries,
                        company_size: parsed?.meta?.company_size || [],
                        content,
                    };
                } catch (error) {
                    const id = file.replace(/\.(yaml|yml)$/, "").replace(/[\\/]/g, "__");
                    return {
                        id,
                        filename: file,
                        name: file,
                        description: "Error parsing file",
                        tags: [],
                        regions: [],
                        countries: [],
                        company_size: [],
                        content,
                    };
                }
            })
        );

        return NextResponse.json({ examples });
    } catch (error) {
        console.error("Error reading examples:", error);
        return NextResponse.json(
            { error: "Failed to load examples", examples: [] },
            { status: 500 }
        );
    }
}
