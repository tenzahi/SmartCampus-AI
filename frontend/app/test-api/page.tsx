
"use client";

import { useEffect, useState } from "react";
import { getHealth } from "../../src/services/api";

export default function TestApiPage() {
  const [result, setResult] = useState("Testing...");

  useEffect(() => {
    getHealth()
      .then((data) => setResult(JSON.stringify(data)))
      .catch((error) => setResult(error.message));
  }, []);

  return (
    <main style={{ padding: "30px" }}>
      <h1>Test Backend API</h1>
      <p>{result}</p>
    </main>
  );
}
