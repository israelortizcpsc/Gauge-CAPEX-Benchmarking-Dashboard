import type { Filters, Meta, Option } from '../lib/api'

interface Props {
  meta: Meta
  filters: Filters
  onChange: (filters: Filters) => void
}

const FIELDS: { key: keyof Filters; label: string; options: (m: Meta) => Option[] }[] = [
  { key: 'sector', label: 'Sector', options: (m) => m.sectors },
  { key: 'region', label: 'Region', options: (m) => m.regions },
  { key: 'project_type', label: 'Project Type', options: (m) => m.project_types },
  { key: 'size_band', label: 'Size Band', options: (m) => m.size_bands },
]

export function FilterBar({ meta, filters, onChange }: Props) {
  const hasFilters = Object.values(filters).some(Boolean)

  return (
    <section className="filters" aria-label="Peer group filters">
      {FIELDS.map((field) => {
        const id = `filter-${field.key}`
        return (
          <div className="field" key={field.key}>
            <label className="field__label" htmlFor={id}>
              {field.label}
            </label>
            <select
              id={id}
              value={filters[field.key] ?? ''}
              onChange={(e) =>
                onChange({ ...filters, [field.key]: e.target.value || undefined })
              }
            >
              <option value="">All</option>
              {field.options(meta).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )
      })}
      <button
        type="button"
        className="filters__reset"
        onClick={() => onChange({})}
        disabled={!hasFilters}
      >
        Reset
      </button>
    </section>
  )
}
