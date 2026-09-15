# Windows Usage Guide

## Requirements

Install 64-bit versions of:

- Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/)
- Java 9 or newer; Java 11 is recommended
- Git, if installing from a cloned repository

Python and Java must use the same architecture. For example, 64-bit Python
requires a 64-bit JVM.

Verify the installations in Command Prompt:

```bat
py --version
java -version
```

If `java` is not found, add the JDK `bin` directory to `PATH` or configure
`JAVA_HOME`, then open a new terminal.

## Install with Command Prompt

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .
demetrapy --help
demetrapy check
```

## Automatic JAR Download

On the first calculation, `demetrapy` downloads this pinned JDemetra+ core
artifact from Maven Central:

```text
https://repo1.maven.org/maven2/eu/europa/ec/joinup/sat/demetra-tstoolkit/2.2.6/demetra-tstoolkit-2.2.6.jar
```

The default Windows cache location is:

```text
C:\Users\YOUR_NAME\.cache\demetrapy\demetra-tstoolkit-2.2.6.jar
```

The automatic download uses the standard Python networking configuration. In a
managed network, `HTTPS_PROXY` may be set for the current Command Prompt
session:

```bat
set "HTTPS_PROXY=http://proxy.example.com:8080"
demetrapy input.csv --output adjusted.csv
```

Do not put proxy passwords or tokens in project configuration files.

## Manual or Offline JAR Installation

Use this workflow when Maven Central is blocked or the target machine has no
internet access.

1. Download `demetra-tstoolkit-2.2.6.jar` from the Maven Central URL above on a
   machine with network access.
2. Transfer the file to the Windows machine through your approved internal file
   transfer process.
3. Store it in a stable location, for example:

```text
C:\Tools\demetrapy\demetra-tstoolkit-2.2.6.jar
```

4. Point `demetrapy` to that exact file.

For the current Command Prompt session:

```bat
set "DEMETRAPY_JAR=C:\Tools\demetrapy\demetra-tstoolkit-2.2.6.jar"
demetrapy input.csv --output adjusted.csv
```

Persist it for future Command Prompt sessions:

```bat
setx DEMETRAPY_JAR "C:\Tools\demetrapy\demetra-tstoolkit-2.2.6.jar"
```

The configured path must identify the JAR file itself, not its directory.
Maven is not required.

### Use the Default Cache Manually

As an alternative to setting an environment variable, create this directory and
place the JAR there with its original filename:

```text
C:\Users\YOUR_NAME\.cache\demetrapy\demetra-tstoolkit-2.2.6.jar
```

The package will detect it and skip the download.

### Remove an Incorrect Override

Command Prompt, current session:

```bat
set DEMETRAPY_JAR=
```

## Run an Adjustment

```bat
demetrapy .\input.csv --config .\examples\configs\x13_basic.json --output .\adjusted.csv
```

For the advanced TRAMO/SEATS configuration, the input CSV must include the
`promotion` column referenced by the example:

```bat
demetrapy .\input.csv --config .\examples\configs\tramoseats_full.json --output .\adjusted.csv
```

The Python API works identically on Windows:

```python
from demetrapy import adjust

result = adjust(
    values,
    frequency="Monthly",
    start_year=2019,
    method="tramoseats",
    spec="RSA4",
)
print(result.seasonally_adjusted.values)
```

## Test the Installation

```bat
python -m unittest discover -s tests
```

## Troubleshooting

Run `demetrapy check` first. It reports Java discovery, Python/Java architecture
compatibility, and the configured or cached JDemetra+ JAR without downloading
or changing anything.

- `DEMETRAPY_JAR does not point to a file`: verify the full path, filename,
  and `.jar` extension. Remove the override to return to automatic downloading.
- `JVMNotFoundException`: install Java and ensure its `bin` directory is on
  `PATH`; restart the terminal afterward.
- `OSError: [WinError 193]`: Python and Java likely use different 32/64-bit
  architectures. Install matching architectures.
- TLS, certificate, proxy, or timeout errors during JAR download: use the manual
  JAR workflow instead of disabling certificate validation.
- `demetrapy` is not recognized: activate `.venv`, or run
  `.\.venv\Scripts\demetrapy.exe` directly.
