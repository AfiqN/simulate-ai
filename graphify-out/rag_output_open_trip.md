# RAG Output — Open Trip Booking Platform

## Stimulus
> Open Trip Booking Platform — Proposal Bisnis

Ringkasan Eksekutif: Open Trip adalah platform digital multi-tenant yang menghubungkan penyelenggara trip petualangan (gunung, laut, alam) dengan calon pe...

## Step 1: LLM Query Generation

Using `generate_perspective_queries()` — LLM generates 2 queries per cluster:

- **trip_organizer**
  - [SENTIMENT] `Indonesia open trip organizer complaints`
  - [CONTEXT] `Indonesia adventure tour market trends`

- **tech_investor**
  - [SENTIMENT] `Indonesia travel startup investor opinions`
  - [CONTEXT] `Indonesia online travel market data`

- **adventure_traveler**
  - [SENTIMENT] `Indonesia open trip traveler reviews`
  - [CONTEXT] `Indonesia adventure tourism traveler trends`

- **saas_competitor**
  - [SENTIMENT] `travel SaaS founder competition views`
  - [CONTEXT] `Indonesia travel booking SaaS landscape`

---

## Step 2: Search Execution + Fact Extraction

### Cluster: `trip_organizer`
*Penyelenggara open trip gunung/laut di Indonesia yang saat ini pakai WhatsApp & spreadsheet, evaluasi apakah platform ini worth it*

#### [SENTIMENT] `Indonesia open trip organizer complaints`

**5 results found:**

  1. [0.77] **mau kemana si | event organizer JAKARTA | Open Trip**
     https://www.maukemanasitour.com/en
     > ilaturahmi Gubernur DKI Jakarta bersama Pasukan Kuning ini merupakan bentuk apresiasi atas dedikasi dan kerja keras dalam menjaga infrastruktur serta ...

  2. [0.76] **What is an Open Trip?. Lately, there has been a rise in demand… | by Treya Indon**
     https://medium.com/@bulp.co/what-is-an-open-trip-330ff1ec9aee
     > You don’t have to worry about the service quality because every Trip Organizer that has partnered up with Treya are professionals who can provide the ...

  3. [0.65] **Open Trip Center, Jakarta, Indonesia - Reviews, Ratings, Tips and Why You Should**
     https://wanderlog.com/place/details/15869017/open-trip-center
     > mation center See all photos About Open Trip Center serves as a fantastic meeting point for travelers looking to embark on exciting adventures. Conven...

  4. [0.65] **Piknik Nusantara Tour & Travel Organizer – Operator Open Trip dan Event Organize**
     https://www.pikniknusantara.co.id/
     > erunya jalan-jalan, dan ciptakan momen tak terlupakan. Select Location Bali Bangka Belitung Banten Bromo Jawa Tengah Jawa Timur Kalimantan Tengah Kepu...

  5. [0.64] **Open Trip & Private Trip Tour Package - IndonesiaJuara**
     https://indonesiajuara.asia/en/
     >  Type of Trip Open Trip Private Trip Search Discover All of Indonesia’s Treasures with Us, Better than Anyone Else! Plan your dream vacation with Indo...

**Extracted Facts:**
  1. [MARKET] Treya Indonesia operates as an Open Trip Marketplace in Indonesia partnering with dozens of Trip Organizers to offer hundreds of open trip packages across Indonesia, indicating a multi-organizer platform model already exists in the market.
  2. [DATA] Piknik Nusantara, an open trip organizer based in Indonesia, has been operating since 2015 (10 years) and serves both FIT (Free Independent Traveler) and GIT (Group Inclusive Tour) segments with 10+ open trip and private trip packages across destinations like Bali, Raja Ampat, Lombok, and Labuan Bajo.
  3. [BEHAVIOR] Open Trip Center in Jakarta is used as a physical meeting point for trip departures, with travelers reporting their first open trip experiences as 'truly memorable' — suggesting strong word-of-mouth and repeat participation behavior among Indonesian adventure travelers.
  4. [SENTIMENT] Treya positions its value proposition partly on trust and service quality assurance (e.g., gender-separated accommodations), implying that service inconsistency and trust gaps with unknown organizers are a real concern for Indonesian open trip participants.

**Sources:**
  - [What is an Open Trip?. Lately, there has been a rise in demand… | by T](https://medium.com/@bulp.co/what-is-an-open-trip-330ff1ec9aee)
  - [Piknik Nusantara Tour & Travel Organizer – Operator Open Trip dan Even](https://www.pikniknusantara.co.id/)
  - [Open Trip Center, Jakarta, Indonesia - Reviews, Ratings, Tips and Why ](https://wanderlog.com/place/details/15869017/open-trip-center)

#### [CONTEXT] `Indonesia adventure tour market trends`

**5 results found:**

  1. [0.76] **Indonesia Travel And Tourism Market Size, Share, Report Forecast 2035**
     https://www.marketresearchfuture.com/reports/indonesia-travel-and-tourism-market-44301
     > h Report: By Type Outlook (Leisure, Educational, Business, Sports, Medical Tourism, Others (Event Travel, Volunteer Travel, etc.)), By Application Out...

  2. [0.64] **Indonesia Online Travel Market Size, Industry Growth, [2033]**
     https://www.imarcgroup.com/indonesia-online-travel-market
     > ravel Market Size, Share, Trends and Forecast by Service Type, Platform, Mode of Booking, Age Group, and Region, 2026-2034 Report Format: PDF+Excel | ...

  3. [0.64] **Indonesia Online Travel Market | 2019 – 2030 | Ken Research**
     https://www.kenresearch.com/indonesia-online-travel-tourism-platforms-market
     > urism Platforms Market Indonesia Online Travel & Tourism Platforms Market is valued at USD 10 Bn, fueled by rising smartphone use, domestic tourism, a...

  4. [0.52] **Adventure tourism rising globally, Indonesia holds strong potential - ANTARA New**
     https://en.antaranews.com/news/380221/adventure-tourism-rising-globally-indonesia-holds-strong-poten
     > g globally, Indonesia holds strong potential September 16, 2025 16:08 GMT+700 Deputy Assistant for Industry Management at the Ministry of Tourism, Bud...

  5. [0.40] **Adventure Tourism Market Size And Share Report 2026-2033**
     https://www.grandviewresearch.com/industry-analysis/adventure-tourism-market-report
     > Countries such as New Zealand and ... and Indonesia attract adventure tourists with offerings such as jungle trekking, diving, and island exploration....

**Extracted Facts:**
  1. [DATA] Indonesia’s travel and tourism market was estimated at USD 5.14 billion in 2024 and is forecast to reach USD 9.04 billion by 2035, with a 5.26% CAGR for 2025–2035.
  2. [DATA] Indonesia’s online travel market reached USD 8,037.4 million in 2025 and is projected to reach USD 17,880.2 million by 2034, growing at a 9.01% CAGR during 2026–2034.
  3. [BEHAVIOR] Indonesia’s online travel growth is attributed to rising digital adoption, a mobile-first consumer base, and demand for frictionless travel experiences, with online channels becoming more popular for flight tickets, hotels, and holiday packages.
  4. [SENTIMENT] On September 16, 2025, Indonesia’s Ministry of Tourism said adventure tourism is increasingly popular among international travelers seeking challenging, authentic experiences tied to culture, and highlighted Indonesia’s strong potential in this segment at the IATTA National Conference in Jakarta.

**Sources:**
  - [Indonesia Travel And Tourism Market Size, Share, Report Forecast 2035](https://www.marketresearchfuture.com/reports/indonesia-travel-and-tourism-market-44301)
  - [Indonesia Online Travel Market Size, Industry Growth, [2033]](https://www.imarcgroup.com/indonesia-online-travel-market)
  - [Adventure tourism rising globally, Indonesia holds strong potential - ](https://en.antaranews.com/news/380221/adventure-tourism-rising-globally-indonesia-holds-strong-potential)


### Cluster: `tech_investor`
*Angel investor/VC lokal yang menilai kelayakan teknis dan potensi pasar platform travel vertikal di Indonesia*

#### [SENTIMENT] `Indonesia travel startup investor opinions`

**5 results found:**

  1. [0.89] **Top 30 Travel Startup Investors in Indonesia in January 2026 — Jan 2026**
     https://shizune.co/investors/travel-investors-indonesia
     > ail, LinkedIn, contact info Excel and CSV export 48,091 investors, updated daily Find investors — It's Free! 28,219+ founders raised $500M+ from: Top ...

  2. [0.64] **Top 50 Startup Investors in Indonesia (June 2026) | Shizune**
     https://shizune.co/investors/investors-indonesia
     > nkedIn, contact info Excel and CSV export 48,091 investors, updated daily Find investors — It's Free! 28,219+ founders raised $500M+ from: Top 50 Star...

  3. [0.59] **Contoh Startup di Indonesia yang Sukses Menarik Investor**
     https://indogencapital.com/contoh-startup-suksdi-indonesia/
     > Traveloka sukses menarik dana dari investor-domestik dan juga asing untuk ekspansi ke negara Asia Tenggara lain. E-commerce lokal ini menjadi salah sa...

  4. [0.52] **Top 20 Startup Investors in Indonesia - Aviaan**
     https://aviaanaccounting.com/top-20-startup-investors-in-indonesia/
     > , a young population, and increasing internet penetration, the country is fostering innovation in sectors like fintech, e-commerce, edtech, and health...

  5. [0.44] **Decoding Indonesia's Travel Sector: Startups That Are Paving The Way**
     https://inc42.com/features/indonesia-travel-startups/
     > re on LinkedIn Share on Email Copy Link Share story [mashshare networks="facebook,twitter,linkedin" services="3"] In-Depth --> FOLLOW US FOLLOW US Add...

**Extracted Facts:**
  1. [EVENT] Traveloka berhasil menarik dana dari investor domestik dan asing untuk ekspansi ke negara-negara Asia Tenggara lain, dan menjadi salah satu unicorn setelah IPO di Bursa Efek Indonesia.
  2. [MARKET] East Ventures adalah salah satu VC paling aktif di Indonesia dengan 131 deal tercatat, berinvestasi di Tokopedia, Traveloka, dan Xendit, dengan ukuran round $649k–$38M.
  3. [SENTIMENT] Indonesia dinilai memiliki 'semua bahan yang tepat' untuk menjadi pasar travel yang tumbuh cepat: populasi 250 juta lebih, pertumbuhan GDP konsisten, ekonomi digital yang berkembang, infrastruktur yang membaik, dan daya beli yang meningkat.
  4. [DATA] Per Juni 2026, database Shizune mencatat 48.091 investor aktif dan lebih dari 28.219 founder yang telah berhasil menghimpun total $500M+, dengan Antler VC sebagai salah satu investor aktif di tahap Pre-Seed hingga Series A untuk startup Software dan AI di Indonesia.

**Sources:**
  - [Contoh Startup di Indonesia yang Sukses Menarik Investor](https://indogencapital.com/contoh-startup-suksdi-indonesia/)
  - [Top 50 Startup Investors in Indonesia (June 2026) | Shizune](https://shizune.co/investors/investors-indonesia)
  - [Decoding Indonesia's Travel Sector: Startups That Are Paving The Way](https://inc42.com/features/indonesia-travel-startups/)
  - [Top 30 Travel Startup Investors in Indonesia in January 2026 — Jan 202](https://shizune.co/investors/travel-investors-indonesia)

#### [CONTEXT] `Indonesia online travel market data`

**5 results found:**

  1. [0.97] **Indonesia Online Travel Market Size, Industry Growth, [2033]**
     https://www.imarcgroup.com/indonesia-online-travel-market
     > ravel Market Size, Share, Trends and Forecast by Service Type, Platform, Mode of Booking, Age Group, and Region, 2026-2034 Report Format: PDF+Excel | ...

  2. [0.93] **Indonesia Online Travel Agency Market Data and Forecasts**
     https://www.reportlinker.com/clp/country/522954/726404
     > Indonesia Online Travel Agency Market Reports 2025 · Unlimited access to 4M Industry, Company and Country reports with daily updates....

  3. [0.89] **Leading online travel agencies Indonesia 2025| Statista**
     https://www.statista.com/statistics/1200620/indonesia-most-used-online-travel-agencies/
     >  technical data (partially from exclusive partnerships). A paid subscription is required for full access. Read more Most used online travel agencies (...

  4. [0.85] **Indonesia Online Travel Booking Service Market Size & Outlook, 2030**
     https://www.grandviewresearch.com/horizon/outlook/online-travel-booking-service-market/indonesia
     > This country databook contains high-level insights into Indonesia online travel booking service market from 2017 to 2030, including revenue numbers, m...

  5. [0.77] **Travel & Tourism - Indonesia | Statista Market Forecast**
     https://www.statista.com/outlook/mmo/travel-tourism/indonesia
     > ta generation volume worldwide 2010-2029 Data centers - statistics & facts TikTok - statistics & facts Top Report View Report Industry Overview Techno...

**Extracted Facts:**
  1. [DATA] Indonesia’s online travel market reached USD 8,037.4 million in 2025.
  2. [DATA] Indonesia’s online travel market is projected to reach USD 17,880.2 million by 2034, implying a 9.01% CAGR during 2026–2034.
  3. [MARKET] IMARC attributes Indonesia online travel market growth to rising digital adoption, a mobile-first consumer base, and growing demand for frictionless travel experiences.
  4. [BEHAVIOR] Online channels are becoming more popular in Indonesia for major travel services including flight tickets, hotels, and holiday packages.

**Sources:**
  - [Indonesia Online Travel Market Size, Industry Growth, [2033]](https://www.imarcgroup.com/indonesia-online-travel-market)


### Cluster: `adventure_traveler`
*Peserta open trip usia 20-35 tahun yang aktif hiking/diving dan sering cari trip via Instagram/WhatsApp grup*

#### [SENTIMENT] `Indonesia open trip traveler reviews`

**5 results found:**

  1. [0.64] **Open Trip Indonesia: 7 Honest Reasons It Beats Regular Tours**
     https://travass.life/open-trip-indonesia-reasons-foreign-travelers-choose/
     > ween Rinca and Siaba. The air is cold and the sky has not fully decided on a color yet. On the forward deck, two people who first met two days ago are...

  2. [0.58] **My trip to Indonesia - Review of Adventure Indonesia, Denpasar, Indonesia - Trip**
     https://www.tripadvisor.com/ShowUserReviews-g297694-d7266962-r445692051-Adventure_Indonesia-Denpasar
     > What to do, where to eat &amp; more trip inspo. ... Review tags are currently only available for English language reviews.Read reviews in EnglishGo ba...

  3. [0.56] **Indonesia Solo Tours & Vacations | Intrepid Travel US**
     https://www.intrepidtravel.com/us/indonesia/solo-travel
     > . Join a local expert on a small group trip with Intrepid and experience the beauty and warmth of Indonesia from a new perspective. Visit both the hot...

  4. [0.52] **Open Trip ID (Jakarta, Indonesia): Hours, Address - Tripadvisor**
     https://www.tripadvisor.com/Attraction_Review-g294229-d20217926-Reviews-Open_Trip_ID-Jakarta_Java.ht
     > *Likely to sell out: Based on Viator’s booking data and information from the provider from the past 30 days, it seems likely this experience will sell...

  5. [0.52] **Reviews of Travels and Travel Agencies in Indonesia - Testimonials | Evaneos**
     https://www.evaneos.co.uk/indonesia/feedback/
     > 019 Indonesia Family See above under best bits The best parts: The enormous variety was very impressive and enjoyable - Ubud rafting, Gili Meno (Maham...

**Extracted Facts:**
  1. [SENTIMENT] Foreign travelers repeatedly return to open trip Indonesia experiences specifically because unplanned social moments between strangers (e.g., two solo travelers from Netherlands and South Korea sharing sunrise on a boat between Rinca and Siaba) cannot be replicated by fixed itineraries.
  2. [DATA] Intrepid Travel's Indonesia small-group trips carry a 4.9/5 rating from 932 reviews, with 'Beautiful Bali' (9 days) priced from USD $848 after discount, indicating strong demand and price sensitivity in the budget-to-mid segment.
  3. [MARKET] Open Trip ID on Tripadvisor is flagged as 'Likely to sell out' based on Viator's 30-day booking data, signaling high near-term demand for open trip products originating from Jakarta.
  4. [SENTIMENT] A family traveler reviewing an Indonesia multi-destination trip complained that 'too much travelling - long car journeys' was a negative, and specifically noted they wished transfer times had been communicated upfront to help with planning.

**Sources:**
  - [Open Trip Indonesia: 7 Honest Reasons It Beats Regular Tours](https://travass.life/open-trip-indonesia-reasons-foreign-travelers-choose/)
  - [Indonesia Solo Tours & Vacations | Intrepid Travel US](https://www.intrepidtravel.com/us/indonesia/solo-travel)
  - [Open Trip ID (Jakarta, Indonesia): Hours, Address - Tripadvisor](https://www.tripadvisor.com/Attraction_Review-g294229-d20217926-Reviews-Open_Trip_ID-Jakarta_Java.html)
  - [Reviews of Travels and Travel Agencies in Indonesia - Testimonials | E](https://www.evaneos.co.uk/indonesia/feedback/)

#### [CONTEXT] `Indonesia adventure tourism traveler trends`

**5 results found:**

  1. [0.88] **Indonesia Travel And Tourism Market Size, Share, Report Forecast 2035**
     https://www.marketresearchfuture.com/reports/indonesia-travel-and-tourism-market-44301
     > h Report: By Type Outlook (Leisure, Educational, Business, Sports, Medical Tourism, Others (Event Travel, Volunteer Travel, etc.)), By Application Out...

  2. [0.77] **Adventure tourism rising globally, Indonesia holds strong potential - ANTARA New**
     https://en.antaranews.com/news/380221/adventure-tourism-rising-globally-indonesia-holds-strong-poten
     > g globally, Indonesia holds strong potential September 16, 2025 16:08 GMT+700 Deputy Assistant for Industry Management at the Ministry of Tourism, Bud...

  3. [0.65] **Indonesia Rises as Adventure Tourism Powerhouse Fueling Economic Growth and Empo**
     https://www.travelandtourworld.com/news/article/indonesia-rises-as-adventure-tourism-powerhouse-fuel
     > Indonesia is rising as a leading adventure tourism powerhouse, attracting travelers from around the world seeking thrilling and immersive experiences....

  4. [0.64] **Travel and tourism in Indonesia - statistics & facts | Statista**
     https://www.statista.com/topics/6871/travel-and-tourism-in-indonesia/
     > facts Region Indonesia Choose a region: Indonesia With its rich culture and attractive natural landscapes across the archipelago, tourism has long bee...

  5. [0.52] **Indonesia Tourism Statistics - How Many Tourists Visit? (2025)**
     https://roadgenius.com/statistics/tourism/indonesia/
     > tunning beaches, rich cultural heritage, vibrant marine life, and adventure-filled landscapes. Overview Toggle How many people visit Indonesia each ye...

**Extracted Facts:**
  1. [DATA] Indonesia’s travel and tourism market was valued at $5.14 billion in 2024 and is forecast to grow from $5.44 billion in 2025 to $9.04 billion by 2035, at a 5.26% CAGR.
  2. [SENTIMENT] Indonesia’s Ministry of Tourism said in September 2025 that adventure tourism is increasingly popular among international travelers who seek challenging, authentic experiences connected to culture, not just leisure.
  3. [DATA] Indonesia received 13.9 million international visitors in 2024, up 18.8% from 11.68 million in 2023 but still about 14% below the 2019 peak of 16.1 million.
  4. [DATA] Indonesia’s international tourism receipts in 2024 increased five-fold compared with 2020, indicating a strong post-pandemic rebound in the tourism industry.

**Sources:**
  - [Indonesia Travel And Tourism Market Size, Share, Report Forecast 2035](https://www.marketresearchfuture.com/reports/indonesia-travel-and-tourism-market-44301)
  - [Adventure tourism rising globally, Indonesia holds strong potential - ](https://en.antaranews.com/news/380221/adventure-tourism-rising-globally-indonesia-holds-strong-potential)
  - [Indonesia Tourism Statistics - How Many Tourists Visit? (2025)](https://roadgenius.com/statistics/tourism/indonesia/)
  - [Travel and tourism in Indonesia - statistics & facts | Statista](https://www.statista.com/topics/6871/travel-and-tourism-in-indonesia/)


### Cluster: `saas_competitor`
*Founder platform booking/travel SaaS yang sudah ada di pasar, menilai diferensiasi dan ancaman kompetitif*

#### [SENTIMENT] `travel SaaS founder competition views`

**5 results found:**

  1. [0.52] **Top 25 B2B SaaS Founder List of 2024**
     https://www.capchase.com/top-25-b2b-saas-founder-list
     > ers highlighted on this list are: ‍ Stand-out leaders innovating in the space Resilient in the face of challenges Driven to pursue excellence Making a...

  2. [0.44] **730+ Funded Travel Startups 2026 | Verified Contacts & Data - Growth List**
     https://growthlist.co/travel-startups/
     > s | US Startup Hubs | By Industry | By Funding Stage Looking for recently funded travel startups? This startup database covers 730+ verified travel co...

  3. [0.44] **How to Compete in SaaS - Stay SaaSy**
     https://blog.staysaasy.com/p/how-to-compete-in-saas
     > lk to customers and put your energy towards making yourself as great as you can be. Hit the gym, practice gratitude, focus on yourself king. At least ...

  4. [0.42] **Micro-SaaS Ideas for Solopreneurs 2026 | by Pallavi Pant | Jan, 2026 | Medium**
     https://medium.com/@pantpallavi13/micro-saas-ideas-for-solopreneurs-2026-e04dd592f606
     > The economics of being a solo founder have never been more attractive. With the maturity of AI-assisted coding and the widespread adoption of no code ...

  5. [0.32] **10 award-winning travel tech startups to watch in 2025**
     https://coaxsoft.com/blog/best-travel-tech-startups
     >  tech startups to watch in 2025 Go to author page Ivan Verkalets CTO, Co-Founder COAX Software Go to author page Maryna Verbovska Content writer 10 aw...

**Extracted Facts:**
  1. [DATA] Travel tech startups raised over $1.8 billion in 2025 across hundreds of deals globally, with 730+ verified funded travel companies tracked as of 2026.
  2. [SENTIMENT] A SaaS competition strategist argues that ignoring competitors in SaaS leads to being 'pillaged' by more aggressive or desperate rivals, stating: 'competitors who are more aggressive, more vicious, or more desperate than you will pillage your customers and put you out of business.'
  3. [BEHAVIOR] Micro-SaaS founders in 2026 are deliberately pursuing vertical specialization in niche industries to avoid competing with horizontal giants like Salesforce, with the explicit strategic rationale of facing 'zero competition' from large players.
  4. [MARKET] The cost to launch a high-performance SaaS app has dropped significantly in 2026 due to AI-assisted coding and no-code frameworks, lowering barriers to entry for new competitors in any vertical.

**Sources:**
  - [730+ Funded Travel Startups 2026 | Verified Contacts & Data - Growth L](https://growthlist.co/travel-startups/)
  - [How to Compete in SaaS - Stay SaaSy](https://blog.staysaasy.com/p/how-to-compete-in-saas)
  - [Micro-SaaS Ideas for Solopreneurs 2026 | by Pallavi Pant | Jan, 2026 |](https://medium.com/@pantpallavi13/micro-saas-ideas-for-solopreneurs-2026-e04dd592f606)

#### [CONTEXT] `Indonesia travel booking SaaS landscape`

**5 results found:**

  1. [0.77] **Indonesia Online Travel & Booking Platforms Market**
     https://www.kenresearch.com/indonesia-online-travel-booking-platforms-market
     > n out Indonesia Online Travel & Booking Platforms Market Indonesia Online Travel & Booking Platforms Market is valued at USD 5 Bn, fueled by smartphon...

  2. [0.77] **SaaS Travel Software | SaaS Booking System | SaaS Solution**
     https://www.travelopro.com/saas-travel-software.php
     > ng Portal Airline Reservation System Cruise Booking System Whatsapp Booking Engine GDS Hotel Extranet Travel Agency Software Hotel CRS Arabic Travel B...

  3. [0.76] **Top 5 Hotel Booking Apps for Indonesia 2026: A Local Expert Guide | Travelnata B**
     https://www.travelnata.com/blog/top-5-hotel-booking-apps-for-your-next-trip-to-indonesia-a-local-exp
     > share Share article All Articles Travel Tips ✓ Live Top 5 Hotel Booking Apps for Your Next Trip to Indonesia: A Local Expert’s Guide G Galuh · Local G...

  4. [0.64] **15 Best Apps for Travel in Indonesia - CARRY ON ONLY**
     https://carryononly.org/15-best-apps-for-travel-in-indonesia/
     > eople and affordable prices. It’s a popular destination for budget conscious and independent travellers. From Bali to Yogyakarta, Komodo National Park...

  5. [0.52] **Leading online travel agencies Indonesia 2025| Statista**
     https://www.statista.com/statistics/1200620/indonesia-most-used-online-travel-agencies/
     >  technical data (partially from exclusive partnerships). A paid subscription is required for full access. Read more Most used online travel agencies (...

**Extracted Facts:**
  1. [DATA] Indonesia's online travel and booking platforms market is valued at USD 5 billion, with growth driven by smartphone adoption and domestic tourism.
  2. [MARKET] Ken Research identifies hotel bookings and individual travelers as key segments in Indonesia's online travel and booking platforms market.
  3. [MARKET] Travelnata describes Traveloka as having “local dominance” in Indonesia’s hotel-booking app landscape, while Agoda is differentiated by “villa-rich inventory.”
  4. [BEHAVIOR] Carry On Only’s Indonesia travel app guide says GoJek is the main ridesharing app the author uses when travelling around Indonesia, indicating traveler reliance on super-app transport tools rather than dedicated trip-booking platforms for local mobility.

**Sources:**
  - [Indonesia Online Travel & Booking Platforms Market](https://www.kenresearch.com/indonesia-online-travel-booking-platforms-market)
  - [Top 5 Hotel Booking Apps for Indonesia 2026: A Local Expert Guide | Tr](https://www.travelnata.com/blog/top-5-hotel-booking-apps-for-your-next-trip-to-indonesia-a-local-experts-guide)
  - [15 Best Apps for Travel in Indonesia - CARRY ON ONLY](https://carryononly.org/15-best-apps-for-travel-in-indonesia/)


---
---

# EXACT PROMPT INJECTION: What Gets Fed to the Swarm Agent Generator

The following text block is the `swarm_rag_perspectives` variable injected
verbatim into the persona-generation prompt that shapes each agent's worldview:

```

STAKEHOLDER PERSPECTIVES (real-world attitudes — use to shape each agent's worldview):

  For cluster "trip_organizer" (Penyelenggara open trip gunung/laut di Indonesia yang saat ini pakai WhatsApp & spreadsheet, evaluasi apakah platform ini worth it):
    - [MARKET] Treya Indonesia operates as an Open Trip Marketplace in Indonesia partnering with dozens of Trip Organizers to offer hundreds of open trip packages across Indonesia, indicating a multi-organizer platform model already exists in the market.
    - [DATA] Piknik Nusantara, an open trip organizer based in Indonesia, has been operating since 2015 (10 years) and serves both FIT (Free Independent Traveler) and GIT (Group Inclusive Tour) segments with 10+ open trip and private trip packages across destinations like Bali, Raja Ampat, Lombok, and Labuan Bajo.
    - [BEHAVIOR] Open Trip Center in Jakarta is used as a physical meeting point for trip departures, with travelers reporting their first open trip experiences as 'truly memorable' — suggesting strong word-of-mouth and repeat participation behavior among Indonesian adventure travelers.
    - [SENTIMENT] Treya positions its value proposition partly on trust and service quality assurance (e.g., gender-separated accommodations), implying that service inconsistency and trust gaps with unknown organizers are a real concern for Indonesian open trip participants.
    - [DATA] Indonesia’s travel and tourism market was estimated at USD 5.14 billion in 2024 and is forecast to reach USD 9.04 billion by 2035, with a 5.26% CAGR for 2025–2035.
    - [DATA] Indonesia’s online travel market reached USD 8,037.4 million in 2025 and is projected to reach USD 17,880.2 million by 2034, growing at a 9.01% CAGR during 2026–2034.
    - [BEHAVIOR] Indonesia’s online travel growth is attributed to rising digital adoption, a mobile-first consumer base, and demand for frictionless travel experiences, with online channels becoming more popular for flight tickets, hotels, and holiday packages.
    - [SENTIMENT] On September 16, 2025, Indonesia’s Ministry of Tourism said adventure tourism is increasingly popular among international travelers seeking challenging, authentic experiences tied to culture, and highlighted Indonesia’s strong potential in this segment at the IATTA National Conference in Jakarta.

  For cluster "tech_investor" (Angel investor/VC lokal yang menilai kelayakan teknis dan potensi pasar platform travel vertikal di Indonesia):
    - [EVENT] Traveloka berhasil menarik dana dari investor domestik dan asing untuk ekspansi ke negara-negara Asia Tenggara lain, dan menjadi salah satu unicorn setelah IPO di Bursa Efek Indonesia.
    - [MARKET] East Ventures adalah salah satu VC paling aktif di Indonesia dengan 131 deal tercatat, berinvestasi di Tokopedia, Traveloka, dan Xendit, dengan ukuran round $649k–$38M.
    - [SENTIMENT] Indonesia dinilai memiliki 'semua bahan yang tepat' untuk menjadi pasar travel yang tumbuh cepat: populasi 250 juta lebih, pertumbuhan GDP konsisten, ekonomi digital yang berkembang, infrastruktur yang membaik, dan daya beli yang meningkat.
    - [DATA] Per Juni 2026, database Shizune mencatat 48.091 investor aktif dan lebih dari 28.219 founder yang telah berhasil menghimpun total $500M+, dengan Antler VC sebagai salah satu investor aktif di tahap Pre-Seed hingga Series A untuk startup Software dan AI di Indonesia.
    - [DATA] Indonesia’s online travel market reached USD 8,037.4 million in 2025.
    - [DATA] Indonesia’s online travel market is projected to reach USD 17,880.2 million by 2034, implying a 9.01% CAGR during 2026–2034.
    - [MARKET] IMARC attributes Indonesia online travel market growth to rising digital adoption, a mobile-first consumer base, and growing demand for frictionless travel experiences.
    - [BEHAVIOR] Online channels are becoming more popular in Indonesia for major travel services including flight tickets, hotels, and holiday packages.

  For cluster "adventure_traveler" (Peserta open trip usia 20-35 tahun yang aktif hiking/diving dan sering cari trip via Instagram/WhatsApp grup):
    - [SENTIMENT] Foreign travelers repeatedly return to open trip Indonesia experiences specifically because unplanned social moments between strangers (e.g., two solo travelers from Netherlands and South Korea sharing sunrise on a boat between Rinca and Siaba) cannot be replicated by fixed itineraries.
    - [DATA] Intrepid Travel's Indonesia small-group trips carry a 4.9/5 rating from 932 reviews, with 'Beautiful Bali' (9 days) priced from USD $848 after discount, indicating strong demand and price sensitivity in the budget-to-mid segment.
    - [MARKET] Open Trip ID on Tripadvisor is flagged as 'Likely to sell out' based on Viator's 30-day booking data, signaling high near-term demand for open trip products originating from Jakarta.
    - [SENTIMENT] A family traveler reviewing an Indonesia multi-destination trip complained that 'too much travelling - long car journeys' was a negative, and specifically noted they wished transfer times had been communicated upfront to help with planning.
    - [DATA] Indonesia’s travel and tourism market was valued at $5.14 billion in 2024 and is forecast to grow from $5.44 billion in 2025 to $9.04 billion by 2035, at a 5.26% CAGR.
    - [SENTIMENT] Indonesia’s Ministry of Tourism said in September 2025 that adventure tourism is increasingly popular among international travelers who seek challenging, authentic experiences connected to culture, not just leisure.
    - [DATA] Indonesia received 13.9 million international visitors in 2024, up 18.8% from 11.68 million in 2023 but still about 14% below the 2019 peak of 16.1 million.
    - [DATA] Indonesia’s international tourism receipts in 2024 increased five-fold compared with 2020, indicating a strong post-pandemic rebound in the tourism industry.

  For cluster "saas_competitor" (Founder platform booking/travel SaaS yang sudah ada di pasar, menilai diferensiasi dan ancaman kompetitif):
    - [DATA] Travel tech startups raised over $1.8 billion in 2025 across hundreds of deals globally, with 730+ verified funded travel companies tracked as of 2026.
    - [SENTIMENT] A SaaS competition strategist argues that ignoring competitors in SaaS leads to being 'pillaged' by more aggressive or desperate rivals, stating: 'competitors who are more aggressive, more vicious, or more desperate than you will pillage your customers and put you out of business.'
    - [BEHAVIOR] Micro-SaaS founders in 2026 are deliberately pursuing vertical specialization in niche industries to avoid competing with horizontal giants like Salesforce, with the explicit strategic rationale of facing 'zero competition' from large players.
    - [MARKET] The cost to launch a high-performance SaaS app has dropped significantly in 2026 due to AI-assisted coding and no-code frameworks, lowering barriers to entry for new competitors in any vertical.
    - [DATA] Indonesia's online travel and booking platforms market is valued at USD 5 billion, with growth driven by smartphone adoption and domestic tourism.
    - [MARKET] Ken Research identifies hotel bookings and individual travelers as key segments in Indonesia's online travel and booking platforms market.
    - [MARKET] Travelnata describes Traveloka as having “local dominance” in Indonesia’s hotel-booking app landscape, while Agoda is differentiated by “villa-rich inventory.”
    - [BEHAVIOR] Carry On Only’s Indonesia travel app guide says GoJek is the main ridesharing app the author uses when travelling around Indonesia, indicating traveler reliance on super-app transport tools rather than dedicated trip-booking platforms for local mobility.

Use these real-world perspectives to shape each agent's memory_vectors and attitudes.
Agents should reflect the genuine sentiments and worldview of their stakeholder group.
Do NOT copy verbatim — synthesize into character-defining beliefs.

```