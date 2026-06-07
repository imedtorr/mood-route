export const COUNTRY_OPTIONS = [
  { name: "Japan", flag: "🇯🇵" },
  { name: "Italy", flag: "🇮🇹" },
  { name: "China", flag: "🇨🇳" },
  { name: "France", flag: "🇫🇷" },
  { name: "Spain", flag: "🇪🇸" },
  { name: "Germany", flag: "🇩🇪" },
  { name: "United Kingdom", flag: "🇬🇧" },
  { name: "United States", flag: "🇺🇸" },
  { name: "South Korea", flag: "🇰🇷" },
  { name: "Thailand", flag: "🇹🇭" },
  { name: "Vietnam", flag: "🇻🇳" },
  { name: "Indonesia", flag: "🇮🇩" },
  { name: "Turkey", flag: "🇹🇷" },
  { name: "Greece", flag: "🇬🇷" },
  { name: "Portugal", flag: "🇵🇹" },
  { name: "Netherlands", flag: "🇳🇱" },
  { name: "Switzerland", flag: "🇨🇭" },
  { name: "Austria", flag: "🇦🇹" },
  { name: "Czech Republic", flag: "🇨🇿" },
  { name: "Poland", flag: "🇵🇱" },
  { name: "Mexico", flag: "🇲🇽" },
  { name: "Brazil", flag: "🇧🇷" },
  { name: "Argentina", flag: "🇦🇷" },
  { name: "Morocco", flag: "🇲🇦" },
  { name: "Egypt", flag: "🇪🇬" },
  { name: "UAE", flag: "🇦🇪" },
  { name: "Singapore", flag: "🇸🇬" },
  { name: "India", flag: "🇮🇳" },
  { name: "Australia", flag: "🇦🇺" },
  { name: "Canada", flag: "🇨🇦" },
  { name: "Norway", flag: "🇳🇴" },
  { name: "Sweden", flag: "🇸🇪" },
  { name: "Denmark", flag: "🇩🇰" },
  { name: "Iceland", flag: "🇮🇸" },
  { name: "Georgia", flag: "🇬🇪" },
  { name: "Armenia", flag: "🇦🇲" },
] as const;

export function countryToFlag(country: string): string {
  return COUNTRY_OPTIONS.find((c) => c.name === country)?.flag ?? "🌍";
}

export function defaultTripName(country: string): string {
  return `${country.trim()} ${new Date().getFullYear()}`;
}
