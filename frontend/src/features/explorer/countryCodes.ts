/**
 * The country identifiers.
 *
 * The boundary file identifies a country by its ISO 3166-1 **numeric** code,
 * because that is how Natural Earth names them; the rest of the application
 * uses the **alpha-2** code. The table below is the translation between the
 * two, for the countries the explorer may show.
 */
export const ISO_NUMERIC_TO_ALPHA: Readonly<Record<string, string>> = {
  '008': 'AL',
  '040': 'AT',
  '056': 'BE',
  '070': 'BA',
  '100': 'BG',
  '112': 'BY',
  '191': 'HR',
  '196': 'CY',
  '203': 'CZ',
  '208': 'DK',
  '233': 'EE',
  '246': 'FI',
  '250': 'FR',
  '276': 'DE',
  '300': 'GR',
  '348': 'HU',
  '352': 'IS',
  '372': 'IE',
  '380': 'IT',
  '428': 'LV',
  '440': 'LT',
  '442': 'LU',
  '470': 'MT',
  '498': 'MD',
  '499': 'ME',
  '528': 'NL',
  '578': 'NO',
  '616': 'PL',
  '620': 'PT',
  '642': 'RO',
  '688': 'RS',
  '703': 'SK',
  '705': 'SI',
  '752': 'SE',
  '756': 'CH',
  '804': 'UA',
  '807': 'MK',
  '826': 'GB',
  '840': 'US',
};

export const ALPHA_TO_ISO_NUMERIC: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(ISO_NUMERIC_TO_ALPHA).map(([numeric, alpha]) => [alpha, numeric]),
);
