# Recommendation system changes

- The API and recommendation service cap responses at five products (or fewer only if the catalogue itself has fewer than five).
- Views, clicks and purchases build a per-user profile with increasing weights: 1.0, 2.5 and 5.0.
- Recent events and dwell time influence the content profile.
- Content similarity, collaborative signals and catalogue popularity are combined.
- Previously interacted products remain eligible as fallback recommendations when the catalogue is small or the user has interacted with most/all products.
- The manual Refresh button sends a distinct refresh seed. It rotates the top-five slate while retaining the relevance ranking, so repeated refreshes visibly change the order.
- Successful interactions trigger an immediate recommendation request. The existing 3-second polling loop also detects updates from background signal processing.
- Cache keys now include model version, signal version and refresh seed to avoid stale recommendation results.

## Rebuild

From the project folder in PowerShell:

```powershell
docker compose up -d --build --force-recreate recommender recommendation frontend
```

Then hard-refresh the browser with Ctrl+Shift+R. The local `.env` is intentionally not included in this archive; keep your existing `.env` file in the project folder.

## Validation

The hybrid recommender tests include cold start, score contributions, popularity, refresh rotation and catalogue fallback.
