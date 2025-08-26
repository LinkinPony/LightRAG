export interface TabVisibilityContextType {
  visibleTabs: Record<string, boolean>;
  setTabVisibility: (tabId: string, isVisible: boolean) => void;
  isTabVisible: (tabId: string) => boolean;
}

// Tag Plan C: shared types
export type TagMap = Record<string, string | string[]>;
export type TagEquals = Record<string, string>;
export type TagIn = Record<string, string[]>;

// Payload extensions (front-end only; API layer will pick needed fields)
export type InsertPayload = {
  text?: string;
  texts?: string[];
  file_source?: string | null;
  file_sources?: string[] | null;
  tags?: TagMap;
};

export type QueryParam = {
  // existing fields are declared in api layer types; keep this minimal to share tag filters
  tag_equals?: TagEquals;
  tag_in?: TagIn;
};
