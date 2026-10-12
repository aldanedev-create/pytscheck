# Support

Read the [documentation index](docs/index.md), [FAQ](docs/faq.md), and [troubleshooting guide](docs/troubleshooting.md). The maintained documentation lives in this repository; a separate Read the Docs deployment is not promised.

For questions or bugs, open a [GitHub issue](https://github.com/aldanedev-create/pytscheck/issues). Include the package/compiler versions from `python -m pytscheck --version`, OS and Python architecture, exact command or code, and minimal source/configuration. Remove secrets and private paths/source before sharing.

For a source checkout, include `python scripts/verify_binaries.py` output when the compiler cannot run. For an installed wheel, include its filename and binary path from `python -m pytscheck --where`.

PyTSCheck relays the pinned compiler's semantics. An upstream compiler issue may need a separate report to Microsoft's TypeScript Go project. Adapter implementation belongs to its consuming package; core support can explain the protocol but does not maintain every integration.

Report vulnerabilities privately through [SECURITY.md](SECURITY.md).
