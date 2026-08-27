import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import api from "../services/api";
import { useAuth } from "./AuthContext";
import { convert, formatCurrency } from "../utils/helpers";

const BASE_CURRENCY = "USD";
const DEFAULT_RATES = { USD: 1, LBP: 89000 };
const RATES_TTL_MS = 6 * 60 * 60 * 1000; // 6 hours

const CURRENCY_CACHE_KEY = "cedarlink_currency";
const RATES_CACHE_KEY = "cedarlink_rates";

const CurrencyContext = createContext(null);

/**
 * The database is the source of truth for an authenticated user's currency.
 * localStorage is only a render cache, namespaced by user id so one account's
 * preference can never be shown for another. It is cleared on logout.
 */
function readCurrencyCache(userId) {
  try {
    const raw = localStorage.getItem(CURRENCY_CACHE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (parsed && parsed.userId === userId && parsed.currency) {
      return parsed.currency;
    }
  } catch {
    /* ignore corrupt cache */
  }
  return null;
}

function writeCurrencyCache(userId, currency) {
  try {
    if (userId == null) {
      localStorage.removeItem(CURRENCY_CACHE_KEY);
      return;
    }
    localStorage.setItem(
      CURRENCY_CACHE_KEY,
      JSON.stringify({ userId, currency }),
    );
  } catch {
    /* storage unavailable */
  }
}

function readRatesCache() {
  try {
    const raw = localStorage.getItem(RATES_CACHE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (
      parsed &&
      parsed.rates &&
      Date.now() - (parsed.savedAt || 0) < RATES_TTL_MS
    ) {
      return parsed.rates;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function CurrencyProvider({ children }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [currency, setCurrencyState] = useState(
    () => readCurrencyCache(userId) || BASE_CURRENCY,
  );
  const [rates, setRates] = useState(() => readRatesCache() || DEFAULT_RATES);
  const [ratesStale, setRatesStale] = useState(false);

  // --- Exchange rates (not user-specific) ---
  useEffect(() => {
    if (readRatesCache()) {
      return;
    }

    let cancelled = false;

    api
      .get("/exchange-rates")
      .then((response) => {
        if (cancelled) return;

        const data = response.data || {};
        const nextRates = data.rates || DEFAULT_RATES;

        setRates(nextRates);
        setRatesStale(Boolean(data.stale));

        try {
          localStorage.setItem(
            RATES_CACHE_KEY,
            JSON.stringify({ rates: nextRates, savedAt: Date.now() }),
          );
        } catch {
          /* storage unavailable */
        }
      })
      .catch(() => {
        if (!cancelled) setRatesStale(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // --- Preferred currency: DB is the source of truth ---
  useEffect(() => {
    if (userId == null) {
      // Guest / just logged out: reset and drop any cached preference.
      setCurrencyState(BASE_CURRENCY);
      writeCurrencyCache(null);
      return;
    }

    // Show the cached value immediately, then confirm against the server.
    const cached = readCurrencyCache(userId);
    if (cached) {
      setCurrencyState(cached);
    } else {
      setCurrencyState(BASE_CURRENCY);
    }

    let cancelled = false;

    api
      .get(`/users/${userId}`)
      .then((response) => {
        if (cancelled) return;

        const serverCurrency = response.data?.user?.currency || BASE_CURRENCY;
        setCurrencyState(serverCurrency);
        writeCurrencyCache(userId, serverCurrency);
      })
      .catch(() => {
        /* keep cached / default value on failure */
      });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  // Called by the settings page after a successful PUT /users/:id/currency.
  const setCurrency = useCallback(
    (nextCurrency) => {
      setCurrencyState(nextCurrency);
      writeCurrencyCache(userId, nextCurrency);
    },
    [userId],
  );

  const value = useMemo(() => {
    const isConverted = currency !== BASE_CURRENCY;

    const convertPrice = (amount, from = BASE_CURRENCY) =>
      convert(Number(amount), from, currency, rates);

    const formatBase = (amount, from = BASE_CURRENCY) =>
      formatCurrency(Number(amount), from);

    const formatConverted = (amount, from = BASE_CURRENCY) => {
      const converted = convertPrice(amount, from);
      return converted == null ? null : formatCurrency(converted, currency);
    };

    return {
      currency,
      baseCurrency: BASE_CURRENCY,
      rates,
      ratesStale,
      isConverted,
      setCurrency,
      convertPrice,
      formatBase,
      formatConverted,
    };
  }, [currency, rates, ratesStale, setCurrency]);

  return (
    <CurrencyContext.Provider value={value}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  const context = useContext(CurrencyContext);

  if (!context) {
    throw new Error("useCurrency must be used within a CurrencyProvider");
  }

  return context;
}
