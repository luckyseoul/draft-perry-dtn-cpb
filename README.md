# Probabilistic Contact Metadata for DTN Bundle Routing

This is the working area for the individual Internet-Draft, "Probabilistic Contact Metadata for DTN Bundle Routing".

* [Editor's Copy](https://luckyseoul.github.io/draft-perry-dtn-cpb/#go.draft-perry-dtn-cpb.html)
* [Datatracker Page](https://datatracker.ietf.org/doc/draft-perry-dtn-cpb)
* [Individual Draft](https://datatracker.ietf.org/doc/html/draft-perry-dtn-cpb)
* [Compare Editor's Copy to Individual Draft](https://luckyseoul.github.io/draft-perry-dtn-cpb/#go.draft-perry-dtn-cpb.diff)

## Contributing

See the
[guidelines for contributions](https://github.com/luckyseoul/draft-perry-dtn-cpb/blob/main/CONTRIBUTING.md).

Contributions can be made by creating pull requests.
The GitHub interface supports creating pull requests using the Edit (✏) button.

## Command Line Usage

Formatted text and HTML versions of the draft can be built using `make`.

```sh
$ make
```

Command line usage requires that you have the necessary software installed.  See
[the instructions](https://github.com/martinthomson/i-d-template/blob/main/doc/SETUP.md).

## Reference Implementation

A reference implementation of the Contact Probability Block encoder/decoder, the
conformance test suite, and the discrete-event simulator that produced the
experimental results in Section 11 of the draft are included under [`impl/`](impl/).

```sh
$ cd impl
$ pip install -r requirements.txt
$ python3 test_cpb.py       # 23 conformance tests, all PASS
$ python3 config1_sim.py    # reproduces Section 11.5 results
```

The reference implementation is provided under the [MIT License](LICENSE). The
draft text itself is governed by the IETF Trust Legal Provisions (BCP 78).
