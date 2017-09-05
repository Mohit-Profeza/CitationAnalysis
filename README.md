# Citation Analysis

Feed PMID from PubMed to Get Citation analysis.

## Getting Started


### Prerequisites

Requirements.txt contains all the packages.

```
NLTK, Re, Requests, BeautifulSoup
```

### How It Works ?


```
from pmc_doi import ParsePMC
# Initialize 
pmc = ParsePMC(20171147) # PMID = 20171147
# Get/Download Citation Data
pmc.get_citations()
# Citation Analysis
pmc.analyze_citation() 
```
