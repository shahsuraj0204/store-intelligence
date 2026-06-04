from app.metrics import calculate_store_metrics
from app.funnel import compute_store_funnel
from app.db import get_db_connection
from datetime import datetime

def generate_store_insights(store_id: str) -> dict:
    metrics = calculate_store_metrics(store_id)
    funnel = compute_store_funnel(store_id)
    
    unique_visitors = metrics["unique_visitors"]
    conversion_rate = metrics["conversion_rate"]
    queue_depth = metrics["queue_depth"]
    abandonment_rate = metrics["abandonment_rate"]
    
    insights = []
    
    # 1. Funnel Dropoff analysis
    if len(funnel) == 4:
        entry_count = funnel[0]["count"]
        zone_count = funnel[1]["count"]
        queue_count = funnel[2]["count"]
        purchase_count = funnel[3]["count"]
        
        # Browse drop-off (entered but didn't visit any zone)
        if entry_count > 0:
            browse_drop = round(((entry_count - zone_count) / entry_count) * 100, 1)
            if browse_drop > 40.0:
                insights.append({
                    "type": "opportunity",
                    "title": "Low Zone Engagement",
                    "priority": "HIGH",
                    "description": f"{browse_drop}% of shoppers entered the store but did not spend time browsing any shelf zones. This indicates poor window display attractiveness or layout friction at the entrance.",
                    "action": "Revise the store entrance visuals and place high-engagement skincare products near the entry aisle."
                })
                
        # Checkout drop-off (browsed but didn't checkout)
        if zone_count > 0:
            checkout_drop = round(((zone_count - queue_count) / zone_count) * 100, 1)
            if checkout_drop > 60.0:
                insights.append({
                    "type": "warning",
                    "title": "High Browse-to-Cart Drop-off",
                    "priority": "CRITICAL",
                    "description": f"{checkout_drop}% of engaged shoppers browsed zones but left without joining the checkout queue. This points to pricing friction or lack of sales assistance.",
                    "action": "Deploy beauty advisors to assist customers in the makeup/skincare aisles and check competitive pricing."
                })
                
    # 2. Queue Abandonment / Service speed
    if abandonment_rate > 15.0:
        insights.append({
            "type": "alert",
            "title": "Checkout Friction Detected",
            "priority": "CRITICAL",
            "description": f"The queue abandonment rate is currently high at {abandonment_rate}%. Customers are leaving the checkout counter without completing purchases.",
            "action": "Increase cashier headcount immediately. Review checkout flow latency to minimize wait times."
        })
    elif queue_depth >= 4:
        insights.append({
            "type": "alert",
            "title": "Billing Bottleneck Building",
            "priority": "HIGH",
            "description": f"There are currently {queue_depth} customers waiting in line. Peak transaction time is approaching.",
            "action": "Open secondary auxiliary checkout counter and activate digital queue-busting solutions."
        })
        
    # 3. Best Performing Zone
    avg_dwells = metrics["avg_dwell_times"]
    if avg_dwells:
        best_zone = max(avg_dwells, key=avg_dwells.get)
        best_dwell_sec = round(avg_dwells[best_zone] / 1000.0, 1)
        insights.append({
            "type": "info",
            "title": f"Engagement Driver: {best_zone}",
            "priority": "MEDIUM",
            "description": f"The {best_zone} zone currently records the highest customer engagement with an average dwell time of {best_dwell_sec} seconds per visitor.",
            "action": "Capitalize on high dwell time by featuring new product launches or high-margin items in this zone."
        })
        
    # 4. Conversion Drop rule
    if unique_visitors >= 5 and conversion_rate < 15.0:
        insights.append({
            "type": "warning",
            "title": "Sub-Target Conversion Rate",
            "priority": "HIGH",
            "description": f"Current store conversion rate is {conversion_rate}%, which is below the target threshold of 25.0%.",
            "action": "Audit current stock levels for top-selling SKUs (Lipsticks, Toners) and verify that checkout systems are online."
        })
        
    # If no warnings/issues, provide default positive insights
    if not insights:
        insights.append({
            "type": "success",
            "title": "Operations Healthy",
            "priority": "LOW",
            "description": "Store KPIs are well within target ranges. Conversion rates and customer dwell engagement are balanced, with no checkout queue delays.",
            "action": "Maintain current staff deployment layout."
        })
        
    return {
        "store_id": store_id,
        "timestamp": datetime.utcnow(),
        "insights": insights
    }
