# FEBE Protocol Reference

Front-End/Back-End protocol specification from Literary Machines 4/63-4/70.

> "This describes the current Xanadu front-end/back-end interface language."
> — Literary Machines 87.1

---

## Overview

FEBE is the protocol between front-ends (user interfaces) and back-ends (storage servers). All operations are expressed in this protocol, and tumblers are the "principal currency."

---

## Basic Formats

### Delimiter

```bnf
<wdelim> ::= '\n'
```

Newline is the general-purpose delimiter throughout the protocol.

### Tumblers

```bnf
<tumbler>      ::= <texp> <tumblerdigit>* <wdelim>
<tumblerdigit> ::= <integer> | <tdelim> <integer>
<tdelim>       ::= '.'
```

Tumblers are period-separated strings of integers.

---

## Address Types

| Type | Description |
|------|-------------|
| `<doc id>` | V-stream address of a document |
| `<link id>` | Address of a link atom |
| `<doc vsa>` | Address of an atom inside a document (V-stream address) |
| `<span>` | Range of addresses (start tumbler + length tumbler) |

### Spans and Sets

```bnf
<span>       ::= <tumbler> <tumbler>

<doc-set>    ::= <ndocs> <doc id>*
<span-set>   ::= <nspans> <span>*
<spec-set>   ::= <nspecs> <spec>*
<spec>       ::= { 's' <wdelim> <span> } | { 'v' <wdelim> <vspec> }

<vspec-set>  ::= <nvspecs> <vspec>*
<vspec>      ::= <doc id> <vspan-set>
<vspan-set>  ::= <nspans> <vspan>*
<vspan>      ::= <span>
```

The `<spec>` uses 's' for span, 'v' for vspec.

### Counts

```bnf
<ndocs>   ::= <integer> <wdelim>
<nspecs>  ::= <integer> <wdelim>
<nvspecs> ::= <integer> <wdelim>
<nspans>  ::= <integer> <wdelim>
```

---

## Content ("Stuff")

"Stuff" is the generic term for things in a document: text and links.

```bnf
<vstuffset> ::= <nthings> <vthing>*
<vthing>    ::= <text> | <link id>

<text-set>  ::= <ntexts> <text>*
<text>      ::= <textflag> <nchars> <char>* <wdelim>
<textflag>  ::= 't'

<ntexts>    ::= <integer> <wdelim>
<nchars>    ::= <integer> <wdelim>
<nthings>   ::= <integer> <wdelim>
```

### Link Sets

```bnf
<from-set>  ::= <span-set>
<to-set>    ::= <span-set>
<home-set>  ::= <span-set>
<three-set> ::= <span-set>
<link-set>  ::= <nlinks> <link id>*
<nlinks>    ::= <integer> <wdelim>
```

Links are described in terms of their end-sets (from, to, three/type).

---

## Operations

### Document Creation

#### CREATENEWDOCUMENT (opcode: 11)

```bnf
CREATENEWDOCUMENT ::= <createdocrequest>
    returns <createdocrequest> <doc id>

<createdocrequest> ::= '11' <wdelim>
```

Creates an empty document. Returns the id of the new document.

#### CREATENEWVERSION (opcode: 13)

```bnf
CREATENEWVERSION ::= <createversionrequest> <doc id>
    returns <createversionrequest> <doc id>

<createversionrequest> ::= '13' <wdelim>
```

Creates a new document with the contents of document `<doc id>`. Returns the id of the new document. **The new document's id will indicate its ancestry.**

---

### Document Modification

#### INSERT (opcode: 0)

```bnf
INSERT ::= <insertrequest> <doc id> <doc vsa> <text set>
    returns <insertrequest>

<insertrequest> ::= '0' <wdelim>
```

Inserts `<text set>` in document `<doc id>` at `<doc vsa>`. The v-stream addresses of any following characters in the document are increased by the length of the inserted text.

#### DELETEVSPAN (opcode: 12)

```bnf
DELETEVSPAN ::= <deleterequest> <doc id> <span>
    returns <deleterequest>

<deleterequest> ::= '12' <wdelim>
```

Removes the given span from the given document.

#### REARRANGE (opcode: 3)

```bnf
REARRANGE ::= <rearrangerequest> <doc id> <cut set>
    returns <rearrangerequest>

<rearrangerequest> ::= '3' <wdelim>
<cut set>          ::= <ncuts> <doc vsa>*
<ncuts>            ::= <integer> <wdelim>   /* ncuts = 3 or 4 */
```

Transposes two regions of text:
- **3 cuts:** Regions are cut1→cut2 and cut2→cut3 (assuming cut1 < cut2 < cut3)
- **4 cuts:** Regions are cut1→cut2 and cut3→cut4 (assuming cut1 < cut2, cut3 < cut4)

#### COPY (opcode: 2)

```bnf
COPY ::= <copyrequest> <doc id> <doc vsa> <spec set>
    returns <copyrequest>

<copyrequest> ::= '2' <wdelim>
```

The material determined by `<spec set>` is copied to the document at the specified address. **This is transclusion** - the copy maintains identity with the original.

#### APPEND (opcode: 19)

```bnf
APPEND ::= <appendrequest> <text set> <doc id>
    returns <appendrequest>

<appendrequest> ::= '19' <wdelim>
```

Appends `<text set>` onto the end of the text space of the document.

---

### Retrieval

#### RETRIEVEV (opcode: 5)

```bnf
RETRIEVEV ::= <retrieverequest> <spec set>
    returns <retrieverequest> <vstuffset>

<retrieverequest> ::= '5' <wdelim>
```

Returns the material (text and links) determined by `<spec set>`.

#### RETRIEVEDOCVSPAN (opcode: 14)

```bnf
RETRIEVEDOCVSPAN ::= <docvspanrequest> <doc id>
    returns <docvspanrequest> <vspan>

<docvspanrequest> ::= '14' <wdelim>
```

Returns a span determining the origin and extent of the V-stream of the document.

#### RETRIEVEDOCVSPANSET (opcode: 1)

```bnf
RETRIEVEDOCVSPANSET ::= <docvspansetrequest> <doc id>
    returns <docvspansetrequest> <vspanset>

<docvspansetrequest> ::= '1' <wdelim>
<vspanset>           ::= <nspans> <vspan>*
```

Returns a span-set indicating both the number of characters of text and the number of links in the document.

---

### Links

#### MAKELINK (opcode: 4)

```bnf
MAKELINK ::= <makelinkrequest> <doc id> <doc vsa>
             <from set> <to set> <three set>
    returns <makelinkrequest> <link id>

<makelinkrequest> ::= '4' <wdelim>
```

Creates a link in `<doc id>` from `<from set>` to `<to set>` connected to `<three set>`. Returns the id of the link made.

**Note:** The document must be specified because that determines the actual residence of the link—a document may contain a link between two other documents.

#### FINDLINKSFROMTOTHREE (opcode: 7)

```bnf
FINDLINKSFROMTOTHREE ::= <linksrequest> <home set>
                         <from set> <to set> <three set>
    returns <linksrequest> <link set>

<linksrequest> ::= '7' <wdelim>
```

Returns all links which are:
1. In `<home set>`
2. From all or any part of `<from set>`
3. To all or any part of `<to set>` and `<three set>`

This is the most powerful link query. If home-set is the whole docuverse, all links between the specified elements are returned.

#### FINDNUMOFLINKSFROMTOTHREE (opcode: 6)

```bnf
FINDNUMOFLINKSFROMTOTHREE ::= <nlinksrequest> <home set>
                              <from set> <to set> <three set>
    returns <nlinksrequest> <nlinks>

<nlinksrequest> ::= '6' <wdelim>
```

Returns the count of matching links (same criteria as FINDLINKSFROMTOTHREE).

#### FINDNEXTNLINKSFROMTOTHREE (opcode: 8)

```bnf
FINDNEXTNLINKSFROMTOTHREE ::= <nextnlinksrequest>
                              <from set> <to set> <three set>
                              <home set> <link id> <nlinks>
    returns <nextnlinksrequest> <linkset>

<nextnlinksrequest> ::= '8' <wdelim>
```

Paginated link retrieval: returns links past `<link id>` in the result list, up to `<nlinks>` items.

#### RETRIEVEENDSETS (opcode: 26)

```bnf
RETRIEVEENDSETS ::= <retrieveendsetsrequest> <spec set>
    returns <retrieveendsetsrequest> <from spec set> <to spec set>

<retrieveendsetsrequest> ::= '26' <wdelim>
<from spec set>          ::= <spec set>
<to spec set>            ::= <spec set>
```

Returns all link end-sets that are in `<spec set>`.

---

### Version Comparison

#### SHOWRELATIONOF2VERSIONS (opcode: 10)

```bnf
SHOWRELATIONOF2VERSIONS ::= <showrelationrequest> <spec set> <spec set>
    returns <showrelationrequest> <correspondence list>

<showrelationrequest>   ::= '10' <wdelim>
<correspondence list>   ::= <ncorrespondences> <correspondence>*
<correspondence>        ::= <doc vsa> <doc vsa> <tumbler>
<ncorrespondences>      ::= <integer> <wdelim>
```

Returns a list of ordered pairs of spans from the two spec-sets that correspond (share common origin).

---

### Document Discovery

#### FINDDOCSCONTAINING (opcode: 22)

```bnf
FINDDOCSCONTAINING ::= <docscontainingrequest> <vspec set>
    returns <docscontainingrequest> <doc set>

<docscontainingrequest> ::= '22' <wdelim>
```

Returns all documents containing any portion of the material included by `<vspec set>`, regardless of where the native copies are located.

---

## Opcode Summary

| Opcode | Operation | Description |
|--------|-----------|-------------|
| 0 | INSERT | Insert text at position |
| 1 | RETRIEVEDOCVSPANSET | Get document span-set |
| 2 | COPY | Copy/transclude content |
| 3 | REARRANGE | Transpose regions |
| 4 | MAKELINK | Create a link |
| 5 | RETRIEVEV | Retrieve content |
| 6 | FINDNUMOFLINKSFROMTOTHREE | Count matching links |
| 7 | FINDLINKSFROMTOTHREE | Find matching links |
| 8 | FINDNEXTNLINKSFROMTOTHREE | Paginated link find |
| 10 | SHOWRELATIONOF2VERSIONS | Compare versions |
| 11 | CREATENEWDOCUMENT | Create empty document |
| 12 | DELETEVSPAN | Delete span |
| 13 | CREATENEWVERSION | Create version copy |
| 14 | RETRIEVEDOCVSPAN | Get document extent |
| 19 | APPEND | Append text |
| 22 | FINDDOCSCONTAINING | Find docs with content |
| 26 | RETRIEVEENDSETS | Get link end-sets |

---

## Notes for Golden Tests

1. **Response format:** Operations echo the request opcode before returning results
2. **Tumbler format:** Period-separated integers, newline-terminated
3. **Counts precede lists:** `<nspans>` before `<span>*`, etc.
4. **Text format:** `'t'` flag, then char count, then chars, then newline
5. **Span = start + length:** Not start + end

---

## References

- Literary Machines 87.1, pages 4/61-4/70
- `udanax-green/green/be_source/fns.c` - Operation implementations
- `udanax-test-harness/febe/` - Protocol client implementation
