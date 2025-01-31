/**
 Convert a Data object to representation
 */
export const getDateTime = (date) => {
  return date.toLocaleString();
};

export const dateTimeTemplate = (row, column) => {
  return getDateTime(new Date(row[column.field]));
};

export const getEngineName = (engine) => {
  // Expect Engine object (see Django Engine serializer)
  return `${engine.provider} (${engine.domain})`;
};

/**
 * Datatable column body template
 * When the value is null/empty, display a placeholder
 */
export const unknownTemplate = (row, column, placeholder) => {
  const value = row[column.field];
  return placeholder
    ? placeholderValue(value, placeholder)
    : placeholderValue(value);
};

export const placeholderValue = (value, placeholder = "Unavailable") => {
  return value || placeholder;
};
