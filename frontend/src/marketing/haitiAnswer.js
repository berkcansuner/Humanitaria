// A real answer the app gave on 2026-11-16, word for word, with its five real
// ReliefWeb sources (titles in each report's own language). Every figure was
// checked against the report it cites. Paragraph breaks are "\n\n" in the text.

export const question = 'How many people are internally displaced in Haiti, and where?'

export const parts = [
  { text: 'In Haiti, as of late 2026, there are an estimated ' },
  { text: '1.5 million internally displaced persons (IDPs)', strong: true },
  { text: ', accounting for approximately 12 percent of the population' },
  { cite: 1 },
  { cite: 2 },
  { cite: 3 },
  { cite: 5 },
  { text: '.\n\nRegarding their locations:\n\n' },
  { text: 'Geographical Distribution:', strong: true },
  {
    text: ' Nearly 80 percent of the displaced population is now located outside of the capital, Port-au-Prince, as violence spreads across the country',
  },
  { cite: 1 },
  { cite: 3 },
  {
    text: '. Earlier data from mid-2026 showed concentrations in the Grand Sud (39%) and Ouest (28%) departments, alongside growing numbers in the Centre and Artibonite departments',
  },
  { cite: 4 },
  { text: '.\n\n' },
  { text: 'Recent Displacement Hotspots:', strong: true },
  {
    text: ' Ongoing armed violence and clashes continue to displace thousands in specific areas. For example, recent attacks have uprooted people in the Artibonite department (including Petite-Rivière de l’Artibonite and Gros Morne) and the Ouest department (including Couyo in Arcahaie and Croix-des-Bouquets on the outskirts of Port-au-Prince)',
  },
  { cite: 1 },
  { cite: 5 },
  {
    text: '.\n\nMost of those displaced are currently staying with host families rather than in displacement sites',
  },
  { cite: 1 },
  { cite: 4 },
  { text: '.' },
]

export const sources = [
  {
    n: 1,
    title: 'Latin America & The Caribbean Weekly Situation Update as of 6 November 2026',
    meta: 'OCHA · Haiti',
    date: '2026-11-06',
    url: 'https://reliefweb.int/report/haiti/latin-america-caribbean-weekly-situation-update-6-november-2026',
  },
  {
    n: 2,
    title: 'WFP Haiti Country Brief, October 2026',
    meta: 'WFP · Haiti',
    date: '2026-11-04',
    url: 'https://reliefweb.int/report/haiti/wfp-haiti-country-brief-october-2026',
  },
  {
    n: 3,
    title:
      'Nuevos datos de la OIM: Cerca de 1,5 millones de personas desplazadas en Haití mientras aumentan los riesgos de huracanes',
    meta: 'IOM · Haiti',
    date: '2026-09-25',
    url: 'https://reliefweb.int/report/haiti/nuevos-datos-de-la-oim-cerca-de-15-millones-de-personas-desplazadas-en-haiti-mientras-aumentan-los-riesgos-de-huracanes',
  },
  {
    n: 4,
    title: 'Haïti : Cluster Abris et Biens non alimentaires - Aperçu de la réponse : aout 2026',
    meta: 'IOM · Haiti',
    date: '2026-09-21',
    url: 'https://reliefweb.int/report/haiti/haiti-cluster-abris-et-biens-non-alimentaires-apercu-de-la-reponse-aout-2026',
  },
  {
    n: 5,
    title:
      'Oficina Integrada de las Naciones Unidas en Haití - Informe del Secretario General (S/2026/800)',
    meta: 'UN Security Council · Haiti',
    date: '2026-10-20',
    url: 'https://reliefweb.int/report/haiti/oficina-integrada-de-las-naciones-unidas-en-haiti-informe-del-secretario-general-s2026800',
  },
]
