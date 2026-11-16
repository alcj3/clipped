import { useEffect, useRef, useState, type FormEvent } from 'react'
import './App.css'

const CATEGORY_NAMES = [
  'Chicken',
  'Beef & pork',
  'Fish & seafood',
  'Dairy',
  'Eggs',
  'Alcohol',
  'Produce',
  'Bread & grains',
  'Snacks',
  'Frozen',
]
const DEFAULT_CATEGORIES = ['Chicken', 'Beef & pork', 'Fish & seafood', 'Dairy', 'Alcohol']
const endDateFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' })

type Deal = {
  id: number | string
  category: string
  name: string
  price: number | null
  price_text: string
  original_price: number | null
  valid_to: string
  image: string
}

type Store = {
  name: string
  count: number
  deals: Deal[]
}

type Status = 'idle' | 'loading' | 'success' | 'empty' | 'error'
type Query = { zip: string; categories: string[] }

function readPreferences() {
  let zip = ''
  let categories = DEFAULT_CATEGORIES
  try {
    zip = window.localStorage.getItem('clipped.zip') ?? ''
    const saved = JSON.parse(window.localStorage.getItem('clipped.categories') ?? 'null')
    if (Array.isArray(saved)) {
      const known = saved.filter(
        (category): category is string => typeof category === 'string' && CATEGORY_NAMES.includes(category),
      )
      if (known.length > 0) categories = known
    }
  } catch {
    // Searching still works when browser privacy settings disable local storage.
  }
  return { zip, categories }
}

function formatPrice(price: number) {
  return `$${price.toFixed(2)}`
}

function priceParts(deal: Deal) {
  if (deal.price === null) return { amount: deal.price_text, prefix: '', suffix: '' }
  const amount = formatPrice(deal.price)
  const position = deal.price_text.indexOf(amount)
  if (position === -1) return { amount, prefix: '', suffix: deal.price_text }
  return {
    amount,
    prefix: deal.price_text.slice(0, position),
    suffix: deal.price_text.slice(position + amount.length),
  }
}

function categoryGroups(deals: Deal[]) {
  const groups = new Map<string, Deal[]>()
  for (const deal of deals) {
    const group = groups.get(deal.category) ?? []
    group.push(deal)
    groups.set(deal.category, group)
  }
  return Array.from(groups.entries())
}

function App() {
  const [initialPreferences] = useState(readPreferences)
  const [zip, setZip] = useState(initialPreferences.zip)
  const [categories, setCategories] = useState(initialPreferences.categories)
  const [editing, setEditing] = useState(false)
  const [zipError, setZipError] = useState('')
  const [categoryError, setCategoryError] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [stores, setStores] = useState<Store[]>([])
  const [lastQuery, setLastQuery] = useState<Query>({ zip: '', categories: [] })
  const [resultVersion, setResultVersion] = useState(0)
  const requestController = useRef<AbortController | null>(null)

  useEffect(() => {
    try {
      window.localStorage.setItem('clipped.zip', zip)
      window.localStorage.setItem('clipped.categories', JSON.stringify(categories))
    } catch {
      // Storage is a convenience, not a requirement for the current search.
    }
  }, [zip, categories])

  useEffect(() => () => requestController.current?.abort(), [])

  function toggleCategory(category: string) {
    setCategories((current) =>
      current.includes(category) ? current.filter((name) => name !== category) : [...current, category],
    )
    setCategoryError('')
  }

  function categoryOrder(category: string) {
    const index = CATEGORY_NAMES.indexOf(category)
    return index === -1 ? CATEGORY_NAMES.length : index
  }

  async function findDeals(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedZip = zip.trim()
    const selected = [...categories].sort((a, b) => categoryOrder(a) - categoryOrder(b))
    setZipError('')
    setCategoryError('')

    if (!/^[0-9]{5}$/.test(normalizedZip)) {
      setZipError('Zip code must be exactly 5 digits.')
      return
    }
    if (selected.length === 0) {
      setCategoryError('Choose at least one category to find deals.')
      return
    }

    requestController.current?.abort()
    const controller = new AbortController()
    requestController.current = controller
    setLastQuery({ zip: normalizedZip, categories: selected })
    setStores([])
    setStatus('loading')
    setEditing(false)

    const parameters = new URLSearchParams({ zip: normalizedZip, categories: selected.join(',') })
    try {
      const response = await fetch(`/api/deals?${parameters}`, { signal: controller.signal })
      if (!response.ok) throw new Error('Flyer request failed')
      const data = (await response.json()) as { stores: Store[] }
      setStores(data.stores)
      setResultVersion((version) => version + 1)
      setStatus(data.stores.length > 0 ? 'success' : 'empty')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setStatus('error')
    } finally {
      if (requestController.current === controller) requestController.current = null
    }
  }

  return (
    <>
      <header className={`topbar${editing ? ' is-editing' : ''}`}>
        <div className="page topbar-inner">
          <h1 className="wordmark">clipped</h1>
          <div className="search-summary">
            <span>Zip {zip.trim() || 'not set'}, {categories.length} {categories.length === 1 ? 'category' : 'categories'}</span>
            <button className="edit-search" type="button" onClick={() => setEditing(true)}>
              Edit search
            </button>
          </div>
          <form className="search-form" onSubmit={findDeals} noValidate>
            <div className="zip-control">
              <label className="control-label" htmlFor="zip">Zip code</label>
              <input
                id="zip"
                name="zip"
                type="text"
                inputMode="numeric"
                autoComplete="postal-code"
                maxLength={5}
                value={zip}
                aria-invalid={Boolean(zipError)}
                aria-describedby={zipError ? 'zip-error' : undefined}
                onChange={(event) => {
                  setZip(event.target.value)
                  setZipError('')
                }}
              />
              {zipError && <p className="field-error" id="zip-error" role="alert">{zipError}</p>}
            </div>
            <fieldset className="category-fieldset" aria-describedby={categoryError ? 'category-error' : undefined}>
              <legend className="control-label">Categories</legend>
              <div className="chip-list">
                {CATEGORY_NAMES.map((category) => (
                  <label className="chip" key={category}>
                    <input
                      type="checkbox"
                      name="category"
                      value={category}
                      checked={categories.includes(category)}
                      onChange={() => toggleCategory(category)}
                    />
                    <span>{category}</span>
                  </label>
                ))}
              </div>
              {categoryError && <p className="field-error" id="category-error" role="alert">{categoryError}</p>}
            </fieldset>
            <button className="find-button" type="submit" disabled={status === 'loading'}>
              Find deals
            </button>
          </form>
        </div>
      </header>

      <main className="page results">
        {status === 'idle' && (
          <p className="first-visit">Enter your zip to see this week's flyer deals near you.</p>
        )}
        {status === 'loading' && (
          <div className="loading-list" role="status" aria-live="polite">
            <span className="visually-hidden">Finding this week's flyer deals.</span>
            <div className="loading-row" aria-hidden="true" />
            <div className="loading-row" aria-hidden="true" />
            <div className="loading-row" aria-hidden="true" />
          </div>
        )}
        {status === 'error' && (
          <p className="source-error" role="alert">
            Couldn't reach the flyer data (Flipp). Your settings are saved, so try Find deals again in a minute.
          </p>
        )}
        {status === 'empty' && (
          <p className="no-results">
            No flyer deals for {lastQuery.categories.join(', ')} near {lastQuery.zip} this week. Try more categories or a nearby zip.
          </p>
        )}
        {status === 'success' && (
          <div className="stores" key={resultVersion}>
            {stores.map((store) => (
              <section className="store" key={store.name} aria-labelledby={`store-${store.name.replace(/[^a-z0-9]/gi, '-')}`}>
                <div className="store-heading">
                  <h2 className="store-name" id={`store-${store.name.replace(/[^a-z0-9]/gi, '-')}`}>{store.name}</h2>
                  <span className="store-count">{store.count} {store.count === 1 ? 'deal' : 'deals'}</span>
                </div>
                {categoryGroups(store.deals).map(([category, deals]) => (
                  <section className="deal-group" key={category}>
                    <h3 className="deal-category">{category}</h3>
                    <ul>
                      {deals.map((deal) => {
                        const parts = priceParts(deal)
                        return (
                          <li className="deal-row" key={deal.id}>
                            <p className="deal-name">{deal.name}</p>
                            <p className="deal-price">
                              {parts.prefix && <span>{parts.prefix}</span>}
                              <span>{parts.amount}</span>
                            </p>
                            <p className="deal-meta">
                              {parts.suffix.trim() && <span>{parts.suffix.trim()}</span>}
                              {deal.original_price !== null && <span>Was {formatPrice(deal.original_price)}</span>}
                              <span>Ends {endDateFormatter.format(new Date(deal.valid_to))}</span>
                            </p>
                          </li>
                        )
                      })}
                    </ul>
                  </section>
                ))}
              </section>
            ))}
          </div>
        )}
      </main>
    </>
  )
}

export default App
