Here is the **OPS RESTful Web Services Reference Guide v 1.3.20** converted into Markdown format.

---

# OPS RESTful Web Services

## Reference Guide v 1.3.20

**June 2024**

**European Patent Office (Europäisches Patentamt / Office européen des brevets)**
Patent Information

Open Patent Services RESTful Web Services

Reference Guide

Version 1.3.20

*Non-confidential* © 2024 European Patent Office

---

## Revision History

| Date | Version | Description |
| --- | --- | --- |
| 01/03/2011 | 1.0.0 | Content development; master draft consultation version |
| 16/05/2011 | 1.0.1 | Update according to changes in the new OPS release |
| 20/06/2011 | 1.0.2 | Update according to changes in the next OPS release |
| 12/12/2011 | 1.0.3 | Update to Family priority-claim response |
| 01/03/2012 | 1.0.4 | Update according to 3.0 OPS release |
| 19/11/2012 | 1.1 | Updated to reflect CPC changes |
| 30/05/2013 | 1.2 | Updated for OPS 3.1 and user Registration |
| 10/10/2013 | 1.2.8 | Corrections to some Registered user response behaviour |
| 08/11/2013 | 1.2.9 | Number Service status codes update |
| 18/11/2013 | 1.2.10 | Timezone specified |
| 16/04/2014 | 1.2.11 | Quota error messages updated |
| 05/09/2014–28/01/2015 | 1.2.12–1.2.14 | Fixed links. Improved information related to image services. CQL queries are updated. Corrected the table with valid combinations of endpoints. CA authority supports fulltext. |
| 24/04/2015–15/01/2016 | 1.2.15–1.2.16 | Register CQL specification link is corrected. Added date formats available in CQL. Added extended CQL section. Minor CQL fixes. Added "cpcc" index. |
| 25/01/2016 | 1.2.17 | Removed `<ops: meta elapsed-time="...">`. Added INPADOC family total-result-count. |
| 16/02/2016 | 1.2.18 | Added new error message RequestTimeout. |
| 15/04/2016 | 1.3.0 | Register UPP information |
| 10/06/2016 | 1.3.1 | Reworked constituents table. Updated CQL examples. |
| 22/05/2017–26/09/2017 | 1.3.2–1.3.4 | Hyperlinks update and encryption protocols. Update the epodoc publication format. Removed all UPP and anonymous access references. Updated description of developer's area. |
| 04/12/2017–04/05/2018 | 1.3.5–1.3.7 | Updated mentions of OPS version 3.1 to 3.2. Added preBRE codes. Fixed inaccuracy in Content-Type header. Removed weekly free quota info for registered users. |
| 03/08/2018–07/05/2019 | 1.3.8–1.3.10 | Updated authentication response view. OPS errors are always in XML format. Updated fulltext collection. |
| 27/05/2019 | 1.3.11 | Added CPC-I. |
| 04/07/2019 | 1.3.12 | Updated CPCI documentation |
| 09/07/2019 | 1.3.13 | Updated fair use link |
| 24/07/2019 | 1.3.14 | Added example with proximity search and relational operators for CPCI |
| 05/09/2019 | 1.3.15 | Updated the fulltext country code list |
| 14/09/2020 | 1.3.16 | Correction to countries list and searching Range limits |
| 16/09/2021 | 1.3.17 | Correction of the text in "Range control" article |
| 24/05/2022 | 1.3.18 | Unitary Patent support |
| 31/05/2023 | 1.3.19 | OPS Register with UPP constituent search identifiers |
| 12/06/2024 | 1.3.20 | Dev Portal UI update |

---

# 1. Introduction

## 1.1. What is OPS?

Open Patent Services (or OPS) provides web services for machine-to-machine queries that deliver production stable patent data from the European Patent Office (EPO). OPS services are free of charge and available 24 hours a day, 7 days a week. Please read the fair use charter for details about using OPS.

### Getting started

Beginning with version 3.0, OPS implements all services with a REST-style architecture. This reference guide aims to provide the information and relevant details you need for automated retrievals of raw patent data using OPS RESTful services.

> **Note:** The request response examples will appear in the browser stylized with XSL, however all responses can be viewed as XML by using 'View source'.

## 1.2. Patent information relevant to OPS

| Concept | Description |
| --- | --- |
| **Patent application** | The formal "paperwork" filed by an applicant seeking to obtain a patent. Includes description and claims. |
| **Patent publication** | The first patent publication is often the published patent application, 18 months after a priority date. Other publications are the patent specification or search report. |
| **Patent priority** | Based on the Paris Convention (1883), applicants have 12 months from first filing to submit subsequent applications and claim the original priority date. |
| **Patent publication kind code** | A code (1 or 2 letters and often a number) distinguishing the kind of published patent document (e.g., A1, B1). |
| **Patent publication date** | The date when a described invention becomes publicly available. |
| **Patent application claims** | The part of the patent that defines the scope of legal protection sought. |
| **Patent citation(s)** | A patent document cited by the applicant or examiner during the granting process (search report, examination, opposition). |
| **Simple patent family** | All documents sharing exactly the same set of priorities. |
| **Patent family** | All documents sharing directly or indirectly at least one priority. |

## 1.3. EP Patent lifecycle and reference types

The lifecycle involves Priority Numbers, Application Numbers, and Publication Numbers.

* **Priority Number (X0):** Information from the priority document serves as the basis.
* **Application Number:** Represented by the electronic file view (D0...D5).
* **Publication Number:** Represents a snapshot of bibliographic data at the time of publication (e.g., A1 Pub, B1 Pub).

*Register data* is the public view of the electronic file when the application enters the public phase (after the first publication).

---

# 2. OPS Concepts

## 2.1. Input

### 2.1.1. Request structure

The generic OPS request URI is constructed as follows:

`protocol/authority/[version]/prefix/service/reference-type/input-format/input/[endpoint]/[constituent(s)]/output-format`

* **protocol**: Usually `http` or `https`.
* **authority**: Usually `ops.epo.org`.
* **version**: Currently `3.2` (in URLs often `3.2`).
* **prefix**: Always `rest-services`.
* **service**: e.g., `published-data`, `family`, `number-service`.
* **reference-type**: `publication`, `application`, or `priority`.
* **input-format**: `original`, `docdb`, or `epodoc`.
* **input**: The identifier (CC, number, KC, date).
* **endpoint** (Optional): e.g., `biblio`, `abstract`, `fulltext`.
* **constituent(s)** (Optional): Response modifiers (separated by commas).
* **output-format**: Used only by the Number-service.

**POST method:** OPS supports POST requests. The input goes into the body.

* Header `Content-Type: text/plain` is mandatory.

### 2.1.2. Input format

* **original**: Domestic numbering format (WIPO ST.10/C). Used only by OPS number-service.
* **docdb**: Derived from original formats; stored in EPO's DOCDB. Pattern: `CC.number.KC.date`.
* **epodoc**: Normalized format for search (EPODOC). Often combines number and kind code.

| Reference type/format | Example |
| --- | --- |
| `application/original` | `MD a 2005 0130` |
| `application/docdb` | `MD.20050130.A` |
| `application/epodoc` | `MD20050000130` |

### 2.1.3. Rules for constructing the input patterns

1. **Concatenation with dots:**
* docdb: `US.92132197.A.19970829` (CC.number.KC.date)


2. **Handling special characters (Brackets):**
* If numbers contain slashes, dots, or commas (e.g., `US08/921,321`), enclose them in brackets: `US.(08/921,321)`.


3. **Encoding:**
* Mandatory encoding: `?` (%3F), `#` (%23), ` ` (Space = %20), `/` (do **not** encode slash in URI paths, but handle properly in original numbers).
* Comma `,` is encoded as `%2C` if part of a number, but used as a separator for constituents.



---

## 2.2. Output

### 2.2.1. Response structure

Responses are encapsulated within `ops:world-patent-data`. The structure depends on the service.
Common elements include:

* `ops:meta`
* `ops:patent-family`
* `ops:document-retrieval`
* `ops:biblio-search`
* `exch:exchange-documents` (Bibliographic data)
* `ftxt:fulltext-documents`
* `reg:register-document`

**JSON Support:**
Add header `Accept: application/json` or append `.json` to the URI. OPS follows BadgerFish convention for XML-to-JSON conversion.

### 2.2.2. Common response structures (XML)

* **Response references:** `application-reference`, `publication-reference`, `priority-claim`.
* **Document-id:** Contains `country`, `doc-number`, `kind`, `date`.
* **Exchange Document:** Uses `exch` namespace. Includes `bibliographic-data` and `abstract`.
* **Bibliographic Data:** Includes `invention-title`, `parties` (applicants/inventors), `classification-ipcr`, `citations`.

### 2.2.3. Error messages

OPS returns XML error messages. Common codes:

* **404:** `CLIENT.Invalid Reference` or `SERVER.EntityNotFound`.
* **400:** `CLIENT.InvalidQuery`.
* **403:** `CLIENT.RobotDetected` or `FORBIDDEN` (Fair Use violation).
* **503:** `SERVER.Limited Server Resources`.

---

## 2.3. Registration & OPS Fair use policy

* **Anonymous users:** No access.
* **Registered users:** Free access up to a quota.
* **Paid users:** Higher volumes available.

### 2.3.1. User Registration

Register at `https://developers.epo.org`. You will receive a **Consumer Key** and **Consumer Secret**.

### 2.3.2. Authentication & Access Token handling

OPS uses OAuth 2.0 (Client Credentials flow).

1. **Base64 Encode:** `Base64(ConsumerKey:ConsumerSecret)`.
2. **Request Token:**
* `POST https://ops.epo.org/3.2/auth/accesstoken`
* Header `Authorization: Basic <Base64String>`
* Body: `grant_type=client_credentials`


3. **Use Token:**
* Response gives `access_token`.
* Use in subsequent requests: `Authorization: Bearer <access_token>`



### 2.3.3. Dynamic fair use monitoring

Headers returned with responses:

* `X-IndividualQuotaPerHour-Used`
* `X-RegisteredQuotaPerWeek-Used`
* `X-Throttling-Control`: Indicates system state (`idle`, `busy`, `overloaded`) and traffic light (`green`, `yellow`, `red`, `black`) for specific services (`retrieval`, `search`, `inpadoc`, `images`).

**Self-throttling:** Clients must monitor `X-Throttling-Control` and adapt request rate to avoid `black` status (suspension).

---

# 3. OPS Services

## 3.1. Published-data services

Retrieves bibliographic data, fulltext, images, and equivalents.

**Endpoints:**

* `biblio`: Bibliographic data (default).
* `abstract`: Patent abstract.
* `fulltext`: Inquiry for description/claims availability.
* `description` / `claims`: Retrieve text.
* `images`: Inquiry and retrieval of PDF/TIFF drawings/documents.
* `equivalents`: Simple patent family.

**Constituents:** `biblio`, `abstract`, `full-cycle`, `images`.

### 3.1.1. Bibliographic data

* **Retrieval:** `GET .../published-data/publication/epodoc/EP1000000.A1/biblio`
* **Bulk:** Use POST with multiple numbers (limit 100).
* **Search:** `GET .../published-data/search?q=applicant=IBM` (Uses CQL).

### 3.1.2. Fulltext inquiry and retrieval

1. **Inquiry:** `GET .../publication/epodoc/EP1000000/fulltext` (Check if `desc="description"` or `desc="claims"` exists).
2. **Retrieval:** `GET .../publication/epodoc/EP1000000/description` or `/claims`.

### 3.1.3. Images inquiry and retrieval

1. **Inquiry:** `GET .../publication/epodoc/EP1000000.A1/images`. Returns `ops:document-instance` with links.
2. **Retrieval:** Use link from inquiry.
* Example: `GET .../published-data/images/EP/1000000/PA/firstpage`
* Full document: Retrieve page-by-page using `X-OPS-Range` header (e.g., `X-OPS-Range: 1`).



### 3.1.4. Equivalents

Retrieves simple patent family. Can combine with constituents: `.../equivalents/biblio`.

---

## 3.2. Family service

Retrieves the **INPADOC extended patent family**.

* **Input formats:** `docdb` or `epodoc` (not original).
* **Constituents:** `biblio`, `legal`.
* **Request:** `GET .../family/publication/docdb/EP.1000000.A1`

---

## 3.3. Number-service

Converts numbers between formats (`original`, `docdb`, `epodoc`).
**Request:** `GET .../number-service/[service]/[input-format]/[input]/[output-format]`
**Example:** `GET .../number-service/application/original/US.(08/921,321).A.19970829/epodoc`

---

## 3.4. Register service

Interface for the **European Patent Register**.

* **Input:** Only `epodoc` format.
* **Constituents:** `biblio`, `procedural-steps`, `events`, `upp` (Unitary Patent).
* **Request:** `GET .../register/application/epodoc/EP99203729`
* **Search:** `GET .../register/search?q=pa=IBM` (Uses Register-specific CQL).

---

## 3.5. Legal service

Retrieves legal data (patent lifecycle/register domain).
**Request:** `GET .../legal/publication/docdb/EP.1000000.A1`

---

## 3.6. Classification services

Retrieves **Cooperative Patent Classification (CPC)** scheme data.

* **Retrieval:** `GET .../classification/cpc/A01B`
* **Search:** `GET .../classification/cpc/search?q=keyword` (Finds CPC classes based on text).
* **Mapping:** `GET .../classification/map/ecla/A61K9/00/cpc` (Maps between ECLA/IPC/CPC).

### 3.7. CPC-I

Supports **CPC International** format (introduced Aug 2019).

* New XML structure for `patent-classifications`.
* Includes `generating-office` attribute (EP, US, CN, KR).
* **Combination sets:** Supported with new structure.
* **Condensed Format:** `?cpci=condensed` query parameter allows grouped generating offices (e.g., `EP,CN,KR,US`).

---

# 4. Appendix

## 4.2. CQL index catalogue (Published-data)

| Index | Description | Example |
| --- | --- | --- |
| `ti` | Title | `ti="green energy"` |
| `ab` | Abstract | `ab=solar` |
| `pa` | Applicant | `pa=IBM` |
| `in` | Inventor | `in=Smith` |
| `pd` | Publication Date | `pd=20051212` or `pd within "2005 2006"` |
| `pn` | Publication Number | `pn=EP1000000` |
| `ap` | Application Number | `ap=EP19990203729` |
| `pr` | Priority Number | `pr=NL1010536` |
| `cpc` | CPC Class | `cpc=A01B` |
| `ipc` | IPC Class | `ipc=A01B` |

## 4.3. Epodoc format

Format: `CCNNNNNNNNNNNN(K)`

* `CC`: Country Code (2 chars).
* `N`: Number (up to 12 digits, right-aligned).
* `K`: Kind code (optional, often attached for utility models or to resolve overlap).
* Example: `EP1915004`

## 4.4. PCT in docdb

Format: `CCccyynnnnnnW`

* `CC`: Country code (e.g., GB, IB).
* `cc`: Century (e.g., 20).
* `yy`: Year.
* `nnnnnn`: Sequence.
* `W`: Mandatory kind code for PCT.
* Example: `PCT/GB02/04635` -> `GB0204635W`