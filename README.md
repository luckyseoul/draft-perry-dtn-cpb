# Bundle Protocol Contact Probability Block

This is the working area for the individual Internet-Draft, "Bundle Protocol
Contact Probability Block".

* [Editor's Copy](https://luckyseoul.github.io/draft-perry-dtn-cpb/#go.draft-perry-dtn-cpb.html)
* [Datatracker Page](https://datatracker.ietf.org/doc/draft-perry-dtn-cpb)
* [Individual Draft](https://datatracker.ietf.org/doc/html/draft-perry-dtn-cpb)
* [Compare Editor's Copy to Individual Draft](https://luckyseoul.github.io/draft-perry-dtn-cpb/#go.draft-perry-dtn-cpb.diff)

## Contributing

See the [guidelines for contributions](CONTRIBUTING.md).

Contributions can be made by creating pull requests. The GitHub interface
supports creating pull requests using the Edit button.

## Command Line Usage

Formatted text, HTML, and PDF versions of the draft can be built using `make`.

```sh
make
```

Command line usage requires the software described in the
[i-d-template setup instructions](https://github.com/martinthomson/i-d-template/blob/main/doc/SETUP.md).

## Reference Implementation

The `impl/` directory contains the CPB CDDL, Python encoder and decoder, and
conformance tests.

```sh
python3 -m pip install -e './impl[test]'
python3 -m pytest -q impl
make cddl
```

See [the implementation documentation](impl/README.md) and the
[CPB quick reference](docs/CPB-QUICK-REFERENCE.md).
