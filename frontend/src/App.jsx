import {useEffect, useState} from "react";

function App() {
  // React state for the backend health check
  const [backendStatus, setBackendStatus] = useState("Checking...");

  // Store the array of race objects returned by the API
  // It starts empty and is filled once the fetch request completes
  const [races, setRaces] = useState([]);

  useEffect(() => {
    // useEffect runs after the component is first rendered
    // The empty dependency array at the end means this runs once on page load

    fetch("http://127.0.0.1:8000/api/health")
      .then(response => response.json())
      .then(data => {
        setBackendStatus(data.status);
      })
      .catch(() => {
        setBackendStatus("Backend unavailable");
      });

    // Request the processed Senate race data from FastAPI
    fetch("http://127.0.0.1:8000/api/races")
      .then(response => response.json())
      .then(data => {
        // Updating state causes React to render the component again,
        // this time with the race data available
        setRaces(data);
      })
      .catch(error => {
        console.error("Failed to load race data:", error);
      });
  }, []);

  return (
    <main>
      <h1>Electoral Analytics Explorer</h1>
      <p>How is campaign spending associated with electoral performance?</p>

      <p>
        Backend status: <strong>{backendStatus}</strong>
      </p>

      <h2>2022 Senate races</h2>

      <table>
        <thead>
          <tr>
            <th>State</th>
            <th>D Spending</th>
            <th>R Spending</th>
            <th>Spending Margin</th>
            <th>Vote Margin</th>
            <th>Winner</th>
          </tr>
        </thead>

        <tbody>
          {/* map() creates one table row for each race object. */}
          {races.map(race => (
            <tr key={`${race.state}-${race.district}`}>
              <td>{race.state}</td>

              {/* Format raw numeric values only for display */}
              <td>${race.dem_spending.toLocaleString()}</td>
              <td>${race.rep_spending.toLocaleString()}</td>

              {/* Margins are stored as proportions, so multiply by 100
                  to display them as percentages */}
              <td>{(race.spending_margin * 100).toFixed(1)}%</td>
              <td>{(race.vote_margin * 100).toFixed(1)}%</td>

              <td>{race.winner_party}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}

export default App;
