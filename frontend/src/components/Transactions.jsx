import { useEffect, useState } from "react";

import { FINANCIAL_YEAR_START_MONTH, financialYearFor } from "../lib/financialYear.js";
import { preciseMoney } from "../lib/format.js";
import { fetchTransactions } from "../lib/transactionsApi.js";

const COLUMNS = ["Date", "Amount", "Type", "Category", "Notes"];

function currentFinancialYear() {
  const today = new Date();
  return financialYearFor(today.getFullYear(), today.getMonth() + 1);
}

export default function Transactions() {
  const [transactions, setTransactions] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    setError(null);
    setTransactions(null);
    fetchTransactions(
      { year: currentFinancialYear(), month: FINANCIAL_YEAR_START_MONTH },
      { signal: controller.signal },
    )
      .then(setTransactions)
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });

    return () => controller.abort();
  }, []);

  if (error !== null) {
    return (
      <section className="card">
        <h3>Transactions</h3>
        <p className="state state--error" role="alert">
          {error}
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>Transactions</h3>

      {transactions === null && <p className="state">Loading the Transactions&hellip;</p>}

      {transactions !== null && transactions.length === 0 && <p className="state">No Transactions yet.</p>}

      {transactions !== null && transactions.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                {COLUMNS.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td>{transaction.date}</td>
                  <td className="table__num">{preciseMoney(transaction.amount)}</td>
                  <td>{transaction.type}</td>
                  <td>{transaction.category}</td>
                  <td>{transaction.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
