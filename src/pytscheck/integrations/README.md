# Integrating generated TypeScript

Adapters belong to the consuming package. PyTSCheck core provides the protocol and checking orchestration but no framework-specific integrations.

The [adapter guide](../../../docs/adapters.md) explains source collection, safe virtual paths, registration, explicit discovery, exceptions, and mapping limitations. The [toy component example](../../../examples/custom_adapter.py) demonstrates extraction; it is not a production parser.

Use `SourceFile` objects containing TypeScript before type information is erased. Generated imports must resolve within the supplied virtual inputs/declarations; the original project's tsconfig and dependencies are not automatically copied into the private temporary directory.

Filename remapping preserves generated line/column values. Full source-map position translation is not implemented. `SourceFile.options` is metadata, not per-file compiler configuration. Empty source lists cannot be checked.

Use the current [Python API](../../../docs/python-api.md) and [compatibility](../../../docs/compatibility.md) contracts when declaring an optional integration dependency. Test discovery against an installed integration package, not only a source checkout.
