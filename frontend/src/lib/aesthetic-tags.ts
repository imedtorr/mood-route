export const KNOWN_AESTHETIC_TAGS = [
  "Architecture",
  "Coffee Culture",
  "Cozy",
  "Creative",
  "Hidden Gem",
  "Luxury",
  "Matcha",
  "Minimal",
  "Neon",
  "Photography",
  "Slow Travel",
  "Vintage",
] as const;

export type AestheticTag = (typeof KNOWN_AESTHETIC_TAGS)[number];

const canonicalSet = new Set<string>(KNOWN_AESTHETIC_TAGS);

export function isCanonicalAestheticTag(tag: string): tag is AestheticTag {
  return canonicalSet.has(tag);
}

export function splitPlaceTags(tags: string[]): { canonical: AestheticTag[]; custom: string[] } {
  const canonical: AestheticTag[] = [];
  const custom: string[] = [];
  for (const tag of tags) {
    if (isCanonicalAestheticTag(tag)) canonical.push(tag);
    else custom.push(tag);
  }
  return { canonical, custom };
}

export function usedCanonicalTags(allTags: string[]): AestheticTag[] {
  const used = new Set(allTags.filter(isCanonicalAestheticTag));
  return KNOWN_AESTHETIC_TAGS.filter((tag) => used.has(tag));
}

/** Canonical tags (fixed order) + legacy/custom tags used on places, for filter dropdown. */
export function usedAestheticFilterTags(allTags: string[]): string[] {
  const canonical = usedCanonicalTags(allTags);
  const custom = [...new Set(allTags.filter((tag) => !isCanonicalAestheticTag(tag)))].sort((a, b) =>
    a.localeCompare(b),
  );
  return [...canonical, ...custom];
}
