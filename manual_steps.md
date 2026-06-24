# Manual Steps: Testing the Award Flight Deal Finder

The codebase has been fully refactored to use the **Seats.aero** API, replacing the failed cash-fare approaches (Duffel/SerpApi). The system now searches for real award availability on Aeroplan, LifeMiles, and United for your FRA → HYD route.

To get this running and test it in the real world, follow these exact steps:

---

## Step 1: Get Your Seats.aero API Key

> **Important**: The Seats.aero API is only available to Pro subscribers ($9.99/month). The free tier does not include API access.

1. Go to [seats.aero](https://seats.aero/) and sign up for an account.
2. Upgrade to a **Pro** subscription.
3. Once subscribed, click on your profile/account icon and navigate to **Settings**.
4. In the left-hand sidebar, click on **API**.
5. Generate a new API key. It will likely look like a long string of letters and numbers (e.g., `pro_123abc...`). Copy this key.

## Step 2: Add the Key to GitHub Secrets

Your GitHub Actions workflow needs this key to authenticate with Seats.aero.

1. Go to your GitHub repository: [github.com/duggirala-max/flights](https://github.com/duggirala-max/flights).
2. Click on **Settings** (the gear icon at the top of the repository page).
3. In the left-hand sidebar, expand **Secrets and variables** and click on **Actions**.
4. Click the green **New repository secret** button.
5. In the **Name** field, enter exactly:
   ```text
   SEATS_AERO_KEY
   ```
6. In the **Secret** field, paste the API key you copied from Seats.aero.
7. Click **Add secret**.

## Step 3: Trigger a Test Run

Now we will test the pipeline to see if it finds any award availability.

1. In your GitHub repository, click on the **Actions** tab.
2. In the left-hand sidebar, click on **Find Flight Deals (Stealth/GDS)**.
3. Click the **Run workflow** dropdown button on the right side.
4. Leave the default parameters (or adjust the dates if you wish) and click the green **Run workflow** button.
5. Wait for the action to complete. You can click on the running job to watch the logs live. You should see it searching `aeroplan`, `lifemiles`, and `united`.

## Step 4: View the Dashboard

1. Once the Action completes successfully, it automatically pushes the new dashboard to GitHub Pages.
2. Open your live dashboard URL: **`https://duggirala-max.github.io/flights/`** (or whichever URL your Pages is hosted at).
3. You should now see a completely revamped dashboard showing:
   - The Award Program (e.g., Aeroplan)
   - The exact Miles Required
   - The Estimated EUR Cost (if you were to buy the miles + taxes)
   - A purple **"Search Award Flight"** button that takes you directly to the airline's redemption page.

---

> **Tip: Understanding the Results**
> If the dashboard says "No flights found," it means there are literally zero Business Class award seats available on FRA→HYD for those specific dates across those programs. This is normal! Award space is highly competitive. Try running the workflow again with a wider date range (e.g., a full month) to see what dates the airlines are actually releasing seats on.
