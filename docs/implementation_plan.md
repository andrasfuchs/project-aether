# **Project Aether: Strategic Implementation of an Agentic Patent Intelligence Framework for Anomalous Hydrogen Phenomena**

## **1\. Executive Strategy and Architectural Philosophy**

### **1.1 The Strategic Mandate: Illuminating the "Unnatural Death" of Patents**

The contemporary landscape of intellectual property (IP) intelligence is undergoing a paradigm shift, moving from passive retrieval to active, agentic reconnaissance. This report outlines a comprehensive implementation strategy for "Project Aether," a bespoke, internal patent search tool designed to operate on a weekly cadence. The primary operational mandate is to monitor, analyze, and interpret patent activity within the highly specific and often obfuscated domain of "sparks in hydrogen"—a terminology frequently serving as a proxy for high-voltage plasma physics, anomalous heat generation, and Low Energy Nuclear Reactions (LENR).

The geographic scope of this surveillance is strictly defined, encompassing the Russian Federation, a geopolitical outlier with a distinct internal patent ecosystem, alongside a strategic corridor of European jurisdictions: Poland, Romania, Czechia, the Netherlands, Spain, Italy, Sweden, Norway, and Finland. The inclusion of these diverse legal frameworks necessitates a tool capable of navigating the disparate patent prosecution highways of the European Patent Office (EPO) members and the isolated, sanction-impacted Rospatent system.

A critical differentiator of this project is its focus on the "negative space" of innovation: rejected patents, withdrawn applications, and discontinued prosecution. In the realm of frontier physics—specifically technologies involving anomalous energy yields from hydrogen interactions—the most valuable intelligence often resides not in the granted patents, which are sanitized for public consumption and commercial viability, but in the rejected applications. These documents, frequently abandoned due to "lack of industrial applicability" or financial constraints, contain raw, unfiltered technical disclosures. Identifying these "unnatural deaths" in the patent lifecycle provides early warning of experimental methodologies that failed regulatory scrutiny but may possess scientific merit.1

### **1.2 The "Antigravity" Paradigm: From Scripting to Orchestration**

Traditional patent monitoring solutions rely on linear scripting—static Python code executing predefined Boolean queries. Such systems are brittle; they fail when API schemas change, struggle with semantic nuances (e.g., distinguishing an automotive spark plug from a plasma electrolysis cathode), and lack the autonomy to pivot when initial searches yield zero results. To address these limitations, Project Aether adopts an agentic architecture inspired by the "Google Antigravity" philosophy, which posits a fundamental transition from the Integrated Development Environment (IDE) as a text editor to a "Mission Control" for autonomous agents.3

In the Antigravity paradigm, the developer shifts from being a "bricklayer" of code to an "architect" of agents. The proposed tool utilizes this "agent-first" approach, where a central "Manager Agent" orchestrates a suite of specialized "Worker Agents" (Researchers, Analysts, Linguists). These agents do not merely execute a search; they plan a research mission. For instance, if a search for "hydrogen spark" in Russia yields high noise from the automotive sector, the Manager Agent autonomously instructs the Researcher Agent to refine the query using negative keywords or specific IPC subclass exclusions (e.g., excluding F02P for internal combustion ignition) before presenting the data to the user.

This approach is facilitated by the generation of "Artifacts"—tangible, structured deliverables created by the agents.4 In our Streamlit-based UI, an Artifact is not a log file but an interactive state object—a dashboard component that the human operator can inspect, verify, and modify. This human-in-the-loop workflow ensures that the system benefits from the speed of AI agent orchestration while retaining the critical judgment of a domain expert, particularly when evaluating the scientific plausibility of "anomalous heat" claims.5

### **1.3 The Technology Stack: Speed, Efficiency, and Modernity**

To realize this vision, the implementation plan prescribes a modern, high-efficiency Python stack. We move beyond legacy package management to utilize uv, a next-generation Python package installer and resolver designed for extreme speed, ensuring that the weekly build and deployment cycles are instantaneous.7 The core reasoning engine will leverage advanced Large Language Models (LLMs) capable of long-context understanding (essential for parsing full patent descriptions), integrated via the Model Context Protocol (MCP).9

The User Interface (UI) will be delivered via Streamlit, chosen for its ability to rapidly prototype data-heavy applications. However, unlike a standard dashboard, this Streamlit interface will function as an agentic workspace, allowing the user to view the "Artifacts" generated by the backend agents, provide feedback (e.g., "Mark this patent as irrelevant"), and trigger deep-dive investigations into specific inventors or assignees using the "Antigravity" browser verification model.10

## **2\. Domain Specificity: The "Spark in Hydrogen" Phenomenon**

### **2.1 Technical Taxonomy and Search Semantics**

The user's query specifies "sparks in hydrogen," "anomalous heat," and "plasma discharge." This terminology sits at the intersection of standard plasma physics and the controversial field of Low Energy Nuclear Reactions (LENR). To build an effective search tool, the agents must be trained to recognize the specific lexicon used by inventors in this field, who often obfuscate their work to avoid immediate rejection by patent examiners trained to flag "cold fusion" as pseudoscientific.

The search strategy must distinguish between three distinct technological clusters that share overlapping terminology:

1. **Standard Industrial Applications:** This includes hydrogen spark ignition for internal combustion engines, high-voltage switching gear (spark gaps), and standard plasma coating technologies. These are "False Positives" and must be aggressively filtered out to prevent alert fatigue.  
2. **Anomalous Plasma Discharge:** Devices describing "excess heat," "over-unity efficiency," or "transmutation" products resulting from electrical discharges in hydrogen or deuterium gas. This is the "True Positive" core target.  
3. **Ambiguous Frontier Physics:** Technologies describing "structured hydrogen," "Rydberg matter," or "condensed plasmoids." These are "Potential Positives" requiring human review.

### **2.2 The "Language of Evasion" and Keyword Strategy**

Inventors in the anomalous heat sector rarely use the term "Cold Fusion." Instead, they employ a "Language of Evasion"—a distinct vocabulary designed to pass the initial formality examination. The agentic system must be equipped with a semantic dictionary that maps these evasive terms to the core search concepts.

| Core Concept | Evasive Terminology (English) | Evasive Terminology (Russian) | Relevance |
| :---- | :---- | :---- | :---- |
| **Cold Fusion** | "Low Energy Nuclear Reaction" (LENR), "Condensed Matter Nuclear Science" (CMNS), "Lattice Assisted Nuclear Reaction" (LANR) | "Холодный ядерный синтез" (Cold Nuclear Synthesis), "Трансмутация элементов" (Transmutation of elements) | **High** |
| **Anomalous Heat** | "Exothermic reaction in metal lattice," "Enthalpy excess," "Anomalous energy release," "Non-chemical heat" | "Аномальное тепловыделение" (Anomalous heat release), "Избыточное энерговыделение" (Excess energy release) | **High** |
| **Spark/Plasma** | "Coherent energy exchange," "Plasmoid generation," "Proton-conductive membrane discharge," "Glow discharge" | "Тлеющий разряд" (Glow discharge), "Плазменный вихрь" (Plasma vortex), "Электролизная плазма" (Electrolysis plasma) | **Critical** |
| **Hydrogen** | "Protium," "Deuterium," "Isotopic hydrogen loading," "Metal hydride saturation" | "Насыщение гидрида" (Hydride saturation), "Изотопы водорода" (Hydrogen isotopes) | **High** |

The search tool must execute Boolean queries that combine these terms while explicitly excluding IPC classes associated with internal combustion engines (e.g., F02P). The agent will dynamically translate these queries into the target languages—Russian, Polish, Czech, Romanian, Dutch, Spanish, Italian, Swedish, Norwegian, and Finnish—to ensure 100% recall across the diverse linguistic landscape of the target jurisdictions.1

### **2.3 Classification Strategy: IPC and CPC Filtering**

To optimize efficiency and speed, the tool cannot rely solely on keyword matching, which is computationally expensive and prone to semantic drift. The "Researcher Agent" will prioritize specific Cooperative Patent Classification (CPC) and International Patent Classification (IPC) codes. The analysis of the provided research material suggests the following high-value classifications:

* **G21B 3/00 (Low temperature nuclear fusion reactors):** This code is explicitly defined for "alleged cold fusion reactors" and "fusion by absorption in a matrix." This is the "Holy Grail" code. Any patent appearing in this class in the target jurisdictions must be flagged immediately, regardless of its legal status.13  
* **H01J 37/00 (Discharge tubes):** This broad class covers tubes for introducing objects to discharge. While generic, it is often the refuge for experimental plasma devices that do not fit into standard energy generation classes. The agent must cross-reference this with keywords like "palladium" or "nickel" to isolate relevant hits.14  
* **H05H 1/00 (Plasma technique):** Covers the generation and manipulation of plasma. This is relevant for "spark in hydrogen" devices that claim to generate anomalous plasma structures (plasmoids).  
* **C25B 1/00 (Electrolytic production of hydrogen):** Many LENR devices operate via electrolysis ("wet" cold fusion). Patents here typically describe the production of hydrogen, but anomalous heat devices will describe the *cathode* interactions (e.g., Palladium) in detail.  
* **H01T (Spark Gaps):** This class is dangerous due to high noise (industrial switches). The agent must only retrieve H01T patents if they co-occur with "hydrogen" (C01B) or "fusion" (G21) classifications.15

## **3\. Geopolitical and Jurisdictional Analysis**

### **3.1 The Russian Federation: A Siloed Ecosystem**

Russia represents the most complex and high-value target in this surveillance operation. The geopolitical landscape following the invasion of Ukraine has led to significant isolation of the Russian patent ecosystem.

#### **3.1.1 Sanctions and Data Isolation**

Following the 2022 invasion, the USPTO and EPO ceased all cooperation with Rospatent, the Russian patent office.16 This cessation means that direct data exchange pipelines may be slower or less reliable. Furthermore, the Russian government issued decrees removing IP protection for patent holders from "unfriendly states" (including all EU members and the US).16 This creates a unique "black box" effect where Western companies may no longer file in Russia, or where Russian inventors may file exclusively domestically to avoid Western scrutiny or sanctions. Therefore, relying on "family data" (patents filed in multiple countries) is no longer a sufficient strategy for Russia; the tool must query Russian domestic databases directly or via aggregators that maintain a persistent connection to Rospatent data, such as Lens.org.18

#### **3.1.2 The "Industrial Applicability" Weapon**

A critical insight for the "sparks in hydrogen" search is the specific mechanism of patent rejection in Russia. The Russian Intellectual Property Court (IPC) and Rospatent frequently use the "industrial applicability" requirement (Article 1352 of the Civil Code) to revoke or refuse patents that lack "sufficient evidence" of the claimed effect.1 In the context of anomalous heat or over-unity efficiency, examiners often cite a lack of conformity with known physical laws as grounds for "non-industrial applicability."

The agentic tool must be programmed to specifically hunt for rejection codes associated with **Article 1352**. A rejection under this article in the field of hydrogen energy is a strong signal that the inventor claimed something "impossible" (i.e., anomalous), making it a high-priority target for this specific search tool. The tool needs to distinguish between a "administrative withdrawal" (Code FA9A \- failure to pay fees) and a "substantive refusal" (Code FC9A \- rejection by examiner).19

### **3.2 Eastern Europe (Poland, Romania, Czechia)**

These jurisdictions are integrated into the European Patent Convention (EPC) but maintain their own national procedures.

* **Poland (PL):** The Polish Patent Office (UPRP) publishes data that is generally accessible via EPO OPS and Lens.org.18 The challenge here is linguistic; Polish technical terminology for "spark discharge" (e.g., *wyładowanie iskrowe*) must be accurately targeted.  
* **Romania (RO) & Czechia (CZ):** Similar to Poland, these countries have active scientific communities in plasma physics. The search tool must ensure that character encoding (UTF-8) handles distinctive characters (e.g., ř, č, ă, ș) correctly to prevent search failures or garbled "Artifact" generation.20

### **3.3 Western Europe & The Nordics (NL, ES, IT, SE, NO, FI)**

In Sweden (SE), Norway (NO), and Finland (FI), the primary challenge is the volume of "Green Hydrogen" patents. These nations are leaders in hydrogen infrastructure and fuel cells.21 A search for "hydrogen" and "spark" here will yield thousands of patents related to hydrogen combustion engines (H2-ICE) or fuel cell ignition systems. To mitigate this, the "Researcher Agent" will apply a "Negative Filter" strategy for these jurisdictions. It will exclude assignees known for automotive manufacturing (e.g., Scania, Volvo) unless the patent specifically cites IPC class G21 (Nuclear/Fusion). This "filtering by assignee" is a crucial efficiency optimization step to ensure the weekly report is not flooded with irrelevant automotive technology.

## **4\. Architectural Blueprint: The Agentic Stack**

### **4.1 The "Manager-Worker" Agent Topology**

The implementation will utilize a hierarchical agent topology, moving away from a single monolithic script. This aligns with the "Antigravity" concept of orchestrating capable, asynchronous agents.4

#### **4.1.1 The Manager Agent (The Orchestrator)**

* **Role:** The Mission Commander. It holds the state of the "Weekly Mission."  
* **Responsibility:**  
  * Maintains the last\_run\_date state.  
  * Decomposes the high-level objective ("Find rejected hydrogen spark patents in Russia and Europe") into sub-tasks.  
  * Assigns tasks to Worker Agents.  
  * Synthesizes the final report.  
* **Reasoning:** "I need to check Russia first. I will deploy the Researcher Agent with the Cyrillic query set. If the API times out, I will retry with a smaller date range."

#### **4.1.2 The Researcher Agent (The Retriever)**

* **Role:** The Tool User. It interfaces with external APIs.  
* **Responsibility:**  
  * Constructs valid JSON queries for Lens.org and Boolean strings for Google Patents.  
  * Handles API authentication and rate limiting (Backoff strategies).22  
  * Retrieves raw JSON data.  
  * **Tools:** LensAPIWrapper, GooglePatentsMCP, EPOSearchTool.

#### **4.1.3 The Analyst Agent (The Interpreter)**

* **Role:** The Domain Expert. It reads and classifies.  
* **Responsibility:**  
  * Parses INPADOC legal status codes (e.g., mapping FC9A to "Substantive Rejection").  
  * Performs semantic analysis on abstracts: "Does this text describe a spark plug or a plasma vortex?"  
  * Translates non-English claims into English.  
  * **Tools:** TranslationEngine, StatusDecoder, RelevanceScorer.

### **4.2 Model Context Protocol (MCP) Integration**

To standardize the interaction between the LLM (the brain of the agents) and the data sources, the tool will implement the Model Context Protocol (MCP).9 MCP acts as a "USB-C port" for AI applications, allowing the agents to connect to local and remote resources seamlessly.

* **Lens.org MCP Server:** We will build a custom Python-based MCP server that wraps the Lens.org API. This allows the LLM to "call" Lens.org functions naturally (e.g., lens.search(query="hydrogen", jurisdiction="RU")) without the Manager Agent needing to know the specific HTTP endpoint details.7  
* **Google Patents MCP:** We will utilize the existing google-patents-mcp (via SerpApi) to allow the agents to cross-reference data. If the Lens MCP returns a "withdrawn" patent, the Analyst Agent can ask the Google Patents MCP: "Is there a US family member for this patent?" to see if the invention is still alive elsewhere.9

### **4.3 The "Artifact" System and Streamlit UI**

In this agentic workflow, the output is not a log stream but a structured "Artifact." The Streamlit UI will be designed to render these Artifacts.

* **The Dashboard Artifact:** A JSON object generated by the Manager Agent containing the week's statistics (e.g., "15 Rejections Found, 3 Anomalous"). Streamlit renders this as a metric row.  
* **The Review Artifact:** A detailed list of the "potential positive" patents. Streamlit renders this as an interactive data grid (using st.data\_editor), allowing the human user to toggle a "Verified" checkbox. This human feedback is fed back to the agent to improve future precision.  
* **The Deep Dive Artifact:** When a user selects a patent, the agent generates a "Deep Dive" artifact—a markdown report summarizing the invention, the reason for rejection (translated from Russian/Polish), and a diagram of the relationship to other patents in the sector.

### **4.4 Python Technology Stack**

* **Core Language:** Python 3.12+ (Utilizing asyncio for concurrent agent execution).  
* **Package Management:** uv (Ultra-fast Python package installer).7 This ensures that the environment setup time is negligible, optimizing for speed as requested.  
* **LLM Orchestration:** LangChain or Google Generative AI SDK (Gemini Pro) for agent reasoning.  
* **Data Layer:**  
  * **SQLite:** Local caching of search results to prevent redundant API calls.  
  * **LanceDB:** A serverless vector database to store the "semantic embeddings" of the patent abstracts.26 This allows the agent to perform "similarity search" (e.g., "Find other patents that sound like this rejected one").  
* **Frontend:** Streamlit.

## **5\. Data Ingestion & Legal Status Forensics**

### **5.1 Primary Data Source: Lens.org**

Lens.org is selected as the primary data source due to its superior aggregation of "legal status" metadata and its generous API limits for research/institutional use.18 Lens aggregates data from EPO (DOCDB/INPADOC), USPTO, and WIPO, providing a single point of entry for the multi-jurisdictional requirement.

* **API Endpoint:** https://api.lens.org/patent/search.28  
* **Key Fields:**  
  * legal\_status.patent\_status: values DISCONTINUED, WITHDRAWN, REJECTED, EXPIRED.28  
  * legal\_status.discontinued\_date: The exact date of death. The agent filters on this field for the current week.29  
  * jurisdiction: Filters for RU, PL, RO, CZ, NL, ES, IT, SE, NO, FI.

### **5.2 Legal Status Forensics: Decoding INPADOC**

The "Analyst Agent" must be a forensic specialist. A patent doesn't just "die"; it leaves a specific code in the INPADOC database.19

**Table 1: Critical INPADOC Codes for Anomalous Hydrogen Search**

| Code | Description | Jurisdiction | Agent Interpretation |
| :---- | :---- | :---- | :---- |
| **FC9A** | Refusal Decision | RU (Russia) | **High Priority:** Substantive rejection. Likely Article 1352 (Industrial Applicability). |
| **FA9A** | Withdrawal (Applicant) | RU (Russia) | **Medium Priority:** Inventor gave up. Possible lack of funds or strategic concealment. |
| **QZ** | Withdrawal | EP (Europe) | **Medium Priority:** Generic withdrawal. |
| **R** | Refusal | EP (Europe) | **High Priority:** Application refused after examination. |
| **MM4A** | Lapsed (No Fee) | PL (Poland) | **Low Priority:** Often administrative. |

The Agent will parse the legal\_status.events array in the Lens API response to identify these specific codes. For Russia, specifically, the presence of FC9A combined with keywords "plasma" or "heat" triggers a "Red Alert" Artifact in the UI.

### **5.3 Handling Multilingual and Cyrillic Data**

* **Encoding:** All Python scripts must explicitly handle UTF-8 encoding. The Lens.org API returns JSON in UTF-8, but intermediate processing (CSV exports, text files) must enforce this to avoid Mojibake (garbled text) with Cyrillic (Russian) or Latin-Extended (Polish/Czech/Romanian) characters.  
* **Transliteration:** The agent will support transliteration (Cyrillic to Latin) for the user interface, but *search* must happen in native scripts.  
* **Translation:** The Analyst Agent will utilize the LLM's translation capabilities to convert the *Abstract* and *Claims* of non-English patents into English for the weekly report. This ensures that a Dutch user can read the rationale for a Russian patent rejection.

## **6\. The Weekly Operational Workflow**

### **6.1 The "Monday Morning" Runbook**

The tool is designed for a weekly cadence, optimizing efficiency by automating the heavy lifting while reserving the final decision for the human expert.

**Step 1: Initialization (Automated \- 09:00 AM)**

* The "Manager Agent" initializes via a cron job or manual trigger in Streamlit.  
* It retrieves the last\_run\_timestamp from the local SQLite database.  
* It defines the search window: \[last\_run\_timestamp\] to \[current\_time\].

**Step 2: The "Researcher" Phase (09:05 AM)**

* The Researcher Agent queries the Lens.org MCP server.  
* **Query 1 (Russia):** (jurisdiction:RU) AND (status:DISCONTINUED OR status:WITHDRAWN) AND (date\_discontinued:\[window\]) AND (keywords\_RU OR keywords\_EN).  
* **Query 2 (Eastern Europe):** (jurisdiction:PL OR RO OR CZ) AND (status:DISCONTINUED) AND...  
* **Query 3 (Western Europe):** (jurisdiction:NL OR ES OR IT OR SE OR NO OR FI) AND (status:DISCONTINUED) AND (NOT assignee:Volvo/Scania/Shell).  
* *Rate Limit Handling:* The agent monitors the x-rate-limit-remaining header. If low, it pauses execution (sleeps) autonomously.23

**Step 3: The "Analyst" Phase (09:20 AM)**

* Raw results are passed to the Analyst Agent.  
* **Decoding:** Legal status codes are parsed. Rejections are separated from withdrawals.  
* **Semantic Scoring:** The LLM evaluates the abstract. "Is this about a spark plug?" (Score: 0). "Is this about plasma interactions in a metal lattice?" (Score: 100).  
* **Artifact Generation:** The agent constructs the JSON payload for the UI.

**Step 4: The "Antigravity" Review (User Action \- 10:00 AM)**

* User logs into the Streamlit dashboard.  
* **View:** The "Rejection Matrix" displays the high-scoring patents.  
* **Verify:** User clicks a "Verify" button. The agent launches a headless browser (using Playwright) to fetch the latest status from the official registry (e.g., Espacenet) to confirm the Lens data is up-to-date.10  
* **Feedback:** User marks hits as "Relevant" or "Noise." This data updates the Vector Database, effectively "training" the agent for next week.

## **7\. Implementation Roadmap: The 12-Week Plan**

### **Phase 1: Foundation (Weeks 1-4)**

* **Week 1:** Setup Python environment with uv. Secure API tokens (Lens, SerpApi). Build LensConnector class.  
* **Week 2:** Implement the MCP Server for Lens.org. Verify connectivity.  
* **Week 3:** Build the Multilingual Query Dictionary (mapping 10 languages).  
* **Week 4:** Develop basic Streamlit UI to display raw API results.

### **Phase 2: Intelligence (Weeks 5-8)**

* **Week 5:** Implement INPADOC status decoding logic (The "Forensic" module).  
* **Week 6:** Integrate the LLM (Gemini Pro) for semantic scoring and translation.  
* **Week 7:** Build the Vector Database (LanceDB) for similarity search.  
* **Week 8:** Refine "Negative Filters" to exclude automotive sparks.

### **Phase 3: Orchestration (Weeks 9-12)**

* **Week 9:** Implement the "Manager Agent" logic (State management, Mission planning).  
* **Week 10:** Create the "Artifact" rendering system in Streamlit.  
* **Week 11:** Implement "Human-in-the-Loop" feedback mechanisms.  
* **Week 12:** Full end-to-end testing and deployment.

## **8\. Risk Assessment and Mitigation**

| Risk | Probability | Impact | Mitigation Strategy |
| :---- | :---- | :---- | :---- |
| **API Rate Limiting** | High | Medium | Implement exponential backoff in the Researcher Agent. Cache results locally in SQLite.31 |
| **Data Latency (Russia)** | High | High | Use Lens.org as primary aggregator, but flag Russian data as "potentially delayed." Cross-reference with Google Patents MCP.16 |
| **False Positives (Auto)** | High | Low | Aggressive negative keyword lists ("Internal Combustion," "Spark Plug"). Filter by IPC codes (Exclude F02). |
| **LLM Hallucination** | Low | High | The LLM is used for *analysis* and *translation*, not *search generation*. Search relies on strict API queries. LLM output is verified by human review. |

## **9\. Conclusion**

Project Aether represents a sophisticated fusion of patent informatics and agentic AI. By moving beyond simple keyword scraping to a semantic, agent-orchestrated workflow, the organization can effectively monitor the "dark matter" of the patent universe—the rejected and withdrawn applications that often harbor the most disruptive, albeit controversial, scientific advances. The use of the "Antigravity" paradigm ensures that the tool is not just a static script but a dynamic intelligence asset, capable of adapting to the shifting geopolitical and technical landscape of anomalous hydrogen research in Europe and Russia.

## ---

**10\. Technical Appendix: Implementation Snippets**

### **10.1 Week 1: The Lens.org Connector (Python)**

Python

import requests  
import asyncio  
import logging  
from tenacity import retry, wait\_exponential, stop\_after\_attempt

\# Configure Logging  
logging.basicConfig(level=logging.INFO)  
logger \= logging.getLogger("ResearcherAgent")

class LensConnector:  
    """  
    The Researcher Agent's primary tool for accessing Lens.org.  
    Implements rate limiting and resilient query execution.  
    """  
    def \_\_init\_\_(self, api\_token: str):  
        self.base\_url \= "https://api.lens.org/patent/search"  
        self.headers \= {  
            "Authorization": f"Bearer {api\_token}",  
            "Content-Type": "application/json"  
        }

    @retry(wait=wait\_exponential(multiplier=1, min=4, max=10), stop=stop\_after\_attempt(5))  
    async def search\_patents(self, query\_payload: dict) \-\> dict:  
        """  
        Executes a search with exponential backoff for rate limits.\[23\]  
        """  
        try:  
            \# Lens API is synchronous, but we wrap it for async agent workflow  
            response \= await asyncio.to\_thread(  
                requests.post,   
                self.base\_url,   
                headers=self.headers,   
                json=query\_payload  
            )  
              
            if response.status\_code \== 429:  
                logger.warning("Rate limit hit. Retrying...")  
                raise Exception("Rate Limit")  
              
            response.raise\_for\_status()  
            return response.json()  
              
        except Exception as e:  
            logger.error(f"Search failed: {e}")  
            raise

    def build\_anomalous\_spark\_query(self, jurisdictions: list, start\_date: str) \-\> dict:  
        """  
        Constructs the complex boolean query for 'Sparks in Hydrogen'.  
        """  
        return {  
            "query": {  
                "bool": {  
                    "must":}}  
                    \],  
                    "should":,  
                    "must\_not": \[  
                        \# Negative Filter for Automotive Noise  
                        {"match\_phrase": {"title": "spark plug"}},  
                        {"match\_phrase": {"abstract": "internal combustion"}}  
                    \],  
                    "minimum\_should\_match": 1  
                }  
            },  
            "size": 50, \# Retrieve 50 candidates for analysis  
            "include": \["lens\_id", "jurisdiction", "doc\_number", "legal\_status", "abstract", "claims"\]  
        }

\# Usage Example  
\# async def main():  
\#     connector \= LensConnector("YOUR\_TOKEN")  
\#     query \= connector.build\_anomalous\_spark\_query(, "2024-01-01")  
\#     results \= await connector.search\_patents(query)  
\#     print(results)

### **10.2 Week 6: The Analyst Agent (Legal Status Decoding)**

Python

def analyze\_legal\_status(patent\_record: dict) \-\> dict:  
    """  
    Decodes INPADOC codes to determine if a patent was 'Refused' or just 'Withdrawn'.  
    Critical for distinguishing failed science from bankrupt inventors.  
    """  
    jurisdiction \= patent\_record.get("jurisdiction")  
    legal\_events \= patent\_record.get("legal\_status", {}).get("events",)  
      
    status\_analysis \= {  
        "is\_refused": False,  
        "is\_withdrawn": False,  
        "refusal\_reason": "Unknown",  
        "code\_found": None  
    }  
      
    for event in legal\_events:  
        code \= event.get("event\_code")  
          
        \# Russia Specific Analysis  
        if jurisdiction \== "RU":  
            if code \== "FC9A": \# Refusal to grant   
                status\_analysis\["is\_refused"\] \= True  
                status\_analysis\["refusal\_reason"\] \= "Substantive Examination Refusal (Likely Art. 1352)"  
                status\_analysis\["code\_found"\] \= code  
                break  
            elif code \== "FA9A": \# Withdrawal  
                status\_analysis\["is\_withdrawn"\] \= True  
                status\_analysis\["code\_found"\] \= code  
          
        \# European / General Analysis  
        elif code in: \# General Refusal codes  
             status\_analysis\["is\_refused"\] \= True  
             status\_analysis\["code\_found"\] \= code  
               
    return status\_analysis

*(End of Report)*

#### **Works cited**

1. Sufficiency of disclosure: unresolved issues in Russia | Kluwer Patent Blog, accessed January 2, 2026, [https://legalblogs.wolterskluwer.com/patent-blog/sufficiency-of-disclosure-unresolved-issues-in-russia/](https://legalblogs.wolterskluwer.com/patent-blog/sufficiency-of-disclosure-unresolved-issues-in-russia/)  
2. What to expect | epo.org, accessed January 2, 2026, [https://www.epo.org/en/new-to-patents/what-to-expect](https://www.epo.org/en/new-to-patents/what-to-expect)  
3. What is Google Antigravity?, accessed January 2, 2026, [https://medium.com/@tahirbalarabe2/what-is-google-antigravity-49872c58305f](https://medium.com/@tahirbalarabe2/what-is-google-antigravity-49872c58305f)  
4. Build with Google Antigravity, our new agentic development platform, accessed January 2, 2026, [https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)  
5. Google Antigravity, accessed January 2, 2026, [https://antigravity.google/](https://antigravity.google/)  
6. Getting Started with Google Antigravity, accessed January 2, 2026, [https://codelabs.developers.google.com/getting-started-google-antigravity](https://codelabs.developers.google.com/getting-started-google-antigravity)  
7. Build an MCP server \- Model Context Protocol, accessed January 2, 2026, [https://modelcontextprotocol.io/docs/develop/build-server](https://modelcontextprotocol.io/docs/develop/build-server)  
8. How to Build MCP Servers in Python: Complete FastMCP Tutorial for AI Developers, accessed January 2, 2026, [https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)  
9. Google Patents MCP Server by KunihiroS \- Glama, accessed January 2, 2026, [https://glama.ai/mcp/servers/@KunihiroS/google-patents-mcp](https://glama.ai/mcp/servers/@KunihiroS/google-patents-mcp)  
10. Google Antigravity: FULLY FREE Agentic Coding Platform\! Cursor Killer\!, accessed January 2, 2026, [https://www.youtube.com/watch?v=U3sTlFaQ1Nw](https://www.youtube.com/watch?v=U3sTlFaQ1Nw)  
11. Tutorial : Getting Started with Google Antigravity, accessed January 2, 2026, [https://medium.com/google-cloud/tutorial-getting-started-with-google-antigravity-b5cc74c103c2](https://medium.com/google-cloud/tutorial-getting-started-with-google-antigravity-b5cc74c103c2)  
12. RU2328519C2 \- Enhanced combustion at vapour phase \- Google Patents, accessed January 2, 2026, [https://patents.google.com/patent/RU2328519C2/en](https://patents.google.com/patent/RU2328519C2/en)  
13. US20210090752A1 \- Low Energy Nuclear Reactor \- Google Patents, accessed January 2, 2026, [https://patents.google.com/patent/US20210090752A1/en](https://patents.google.com/patent/US20210090752A1/en)  
14. IET \- IPC Codes Applied in Inspec Records 2025, accessed January 2, 2026, [https://www.theiet.org/media/fpleg2vr/ipc-patent-codes.pdf](https://www.theiet.org/media/fpleg2vr/ipc-patent-codes.pdf)  
15. CPC Scheme \- H ELECTRICITY \- USPTO, accessed January 2, 2026, [https://www.uspto.gov/web/patents/classification/cpc/html/cpc-H.html](https://www.uspto.gov/web/patents/classification/cpc/html/cpc-H.html)  
16. Russian Decree Undermines Value of Certain Patents; USPTO Cuts All Ties with Russian Patent Office \- Morgan Lewis, accessed January 2, 2026, [https://www.morganlewis.com/pubs/2022/04/russian-decree-undermines-value-of-certain-patents-uspto-cuts-all-ties-with-russian-patent-office](https://www.morganlewis.com/pubs/2022/04/russian-decree-undermines-value-of-certain-patents-uspto-cuts-all-ties-with-russian-patent-office)  
17. Russia Issues Decree Affecting IP Rights for "Unfriendly Countries" | Law Bulletins, accessed January 2, 2026, [https://www.taftlaw.com/news-events/law-bulletins/russia-issues-decree-affecting-ip-rights-for-unfriendly-countries/](https://www.taftlaw.com/news-events/law-bulletins/russia-issues-decree-affecting-ip-rights-for-unfriendly-countries/)  
18. Lens.org \- Patents | WIPO Inspire, accessed January 2, 2026, [https://inspire.wipo.int/lensorg-patents](https://inspire.wipo.int/lensorg-patents)  
19. Model Table \- WIPO, accessed January 2, 2026, [https://www.wipo.int/edocs/mdocs/classifications/es/cws\_6/cws\_6\_13-annex1.xlsx](https://www.wipo.int/edocs/mdocs/classifications/es/cws_6/cws_6_13-annex1.xlsx)  
20. Grant/refusal \- Fillun, accessed January 2, 2026, [https://www.fillun.com/grant-refusal](https://www.fillun.com/grant-refusal)  
21. Hydrogen Technologies Safety Guide \- Publications, accessed January 2, 2026, [https://docs.nrel.gov/docs/fy15osti/60948.pdf](https://docs.nrel.gov/docs/fy15osti/60948.pdf)  
22. API Rate Limits \- Open Data Portal \- USPTO, accessed January 2, 2026, [https://data.uspto.gov/apis/api-rate-limits](https://data.uspto.gov/apis/api-rate-limits)  
23. Institutional Toolkit Subscriber Onboarding – The Lens, accessed January 2, 2026, [https://support.lens.org/knowledge-base/onboarding-institutional-toolkit-subscribers/](https://support.lens.org/knowledge-base/onboarding-institutional-toolkit-subscribers/)  
24. Introducing the Model Context Protocol \- Anthropic, accessed January 2, 2026, [https://www.anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol)  
25. How to Build a Python MCP Server to Query a Knowledge Base \- YouTube, accessed January 2, 2026, [https://www.youtube.com/watch?v=0CWAzbduYZs](https://www.youtube.com/watch?v=0CWAzbduYZs)  
26. Context Lens | Awesome MCP Servers, accessed January 2, 2026, [https://mcpservers.org/servers/cornelcroi/context-lens](https://mcpservers.org/servers/cornelcroi/context-lens)  
27. Refine Patent Search \- Lens – Support, accessed January 2, 2026, [https://support.lens.org/knowledge-base/refine-patent-search/](https://support.lens.org/knowledge-base/refine-patent-search/)  
28. lens-api-doc/patent-api-doc.md at master · cambialens/lens-api-doc \- GitHub, accessed January 2, 2026, [https://github.com/cambialens/lens-api-doc/blob/master/patent-api-doc.md](https://github.com/cambialens/lens-api-doc/blob/master/patent-api-doc.md)  
29. Patent Response \- Lens API Documentation, accessed January 2, 2026, [https://docs.api.lens.org/response-patent.html](https://docs.api.lens.org/response-patent.html)  
30. INPADOC classification scheme | epo.org, accessed January 2, 2026, [https://www.epo.org/en/searching-for-patents/helpful-resources/first-time-here/legal-event-data/inpadoc-classification-scheme](https://www.epo.org/en/searching-for-patents/helpful-resources/first-time-here/legal-event-data/inpadoc-classification-scheme)  
31. Support \- Lens API Documentation, accessed January 2, 2026, [https://docs.api.lens.org/support.html](https://docs.api.lens.org/support.html)