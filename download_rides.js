// Paste this into your browser console at https://account.citibikenyc.com/ride-history
// It will download a JSON file with ALL your ride history.

// CONFIGURATION
const CUTOFF_DATE = 0; // No cutoff — grab everything
const DELAY_MS = 1000; // 1 second delay between requests

// GRAPHQL QUERIES
const QUERY_LIST = `query GetCurrentUserRides($startTimeMs: String, $memberId: String) {
  member(id: $memberId) {
    id
    rideHistory(startTimeMs: $startTimeMs) {
      limit
      hasMore
      rideHistoryList {
        rideId
        startTimeMs
        endTimeMs
        price { formatted }
        duration
        rideableName
      }
    }
  }
}`;

const QUERY_DETAILS = `query GetCurrentUserRideDetails($rideId: String!) {
  me {
    rideDetails(rideId: $rideId) {
      rideId
      startAddressStr
      endAddressStr
      paymentBreakdownMap {
        lineItems {
          title
          amount { formatted }
        }
      }
    }
  }
}`;

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function fetchGQL(payload) {
  const response = await fetch(window.location.origin + "/bikesharefe-gql", {
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    method: "POST"
  });
  return await response.json();
}

async function scrapeRideHistory() {
  console.log("Starting Ride History Export...");

  let allRides = [];
  let hasMore = true;
  let nextCursor = String(Date.now());

  // Phase 1: Get all rides
  while (hasMore) {
    console.log(`Fetching rides before ${new Date(parseInt(nextCursor)).toLocaleString()}...`);

    const res = await fetchGQL({
      operationName: "GetCurrentUserRides",
      query: QUERY_LIST,
      variables: { startTimeMs: nextCursor }
    });

    if (res.errors) { console.error("API Error:", res.errors); break; }
    if (!res.data?.member) { console.error("Unexpected response:", res); break; }

    const history = res.data.member.rideHistory;
    const rides = history.rideHistoryList;

    if (!rides || rides.length === 0) { console.log("No more rides."); break; }

    allRides.push(...rides);
    console.log(`Found ${rides.length} rides (total: ${allRides.length})`);

    const lastRideTime = parseInt(rides[rides.length - 1].startTimeMs);
    if (lastRideTime < CUTOFF_DATE) {
      hasMore = false;
    } else {
      hasMore = history.hasMore;
      nextCursor = rides[rides.length - 1].startTimeMs;
    }

    await sleep(DELAY_MS);
  }

  console.log(`Found ${allRides.length} total rides. Fetching details...`);

  // Phase 2: Enrich with addresses
  const detailedRides = [];

  for (let i = 0; i < allRides.length; i++) {
    const ride = allRides[i];
    if (i % 10 === 0) console.log(`Details: ${i}/${allRides.length} (${Math.round((i/allRides.length)*100)}%)`);

    try {
      const detailRes = await fetchGQL({
        operationName: "GetCurrentUserRideDetails",
        query: QUERY_DETAILS,
        variables: { rideId: ride.rideId }
      });

      const details = detailRes.data?.me?.rideDetails;
      if (details) {
        detailedRides.push({
          ...ride,
          startAddress: details.startAddressStr,
          endAddress: details.endAddressStr,
          lineItems: details.paymentBreakdownMap?.lineItems || []
        });
      } else {
        detailedRides.push(ride);
      }
    } catch (e) {
      console.warn(`Failed details for ride ${ride.rideId}`, e);
      detailedRides.push(ride);
    }

    await sleep(DELAY_MS);
  }

  // Phase 3: Download JSON
  console.log(`Done! Downloading ${detailedRides.length} rides...`);
  const blob = new Blob([JSON.stringify(detailedRides, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `citibike_rides_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
}

scrapeRideHistory();
