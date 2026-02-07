import streamlit as st
import pandas as pd


def render_results_tab(assessments, jurisdiction_map):
    if not assessments:
        st.info("No results yet. Run an analysis to populate the table.")
        return

    # Sort assessments by relevance_score descending
    sorted_assessments = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)

    # Reverse mapping from code to jurisdiction name
    jurisdiction_code_to_name = {v: k for k, v in jurisdiction_map.items()}
    # Special handling for WO jurisdiction
    jurisdiction_code_to_name["WO"] = "WO - PCT application"

    # Prepare data for dataframe
    data = []
    for a in sorted_assessments:
        # Convert jurisdiction code to name
        jurisdiction_name = jurisdiction_code_to_name.get(a.jurisdiction, a.jurisdiction)

        # Format title: capitalize first letter, rest lowercase
        formatted_title = a.title.capitalize() if a.title else ""

        # Format inventors: title case (each word starts with capital)
        formatted_inventors = ", ".join([inv.title() for inv in a.inventors]) if a.inventors else "Unknown"

        # Determine status with original status for "Other" category
        if a.status_analysis.is_refused:
            status_display = "Refused"
        elif a.status_analysis.is_withdrawn:
            status_display = "Withdrawn"
        elif a.status_analysis.is_expired:
            status_display = "Expired"
        elif a.status_analysis.is_inactive:
            status_display = "Inactive"
        elif a.status_analysis.is_active:
            status_display = "Active"
        elif a.status_analysis.is_pending:
            status_display = "Pending"
        else:
            # For "Other" status, include original status if available
            original = a.status_analysis.original_status or "UNKNOWN"
            status_display = f"Other ({original})"

        row = {
            "Lens ID": a.lens_id,
            "Patent #": a.doc_number,
            "Title": formatted_title,
            "Inventor(s)": formatted_inventors,
            "Jurisdiction": jurisdiction_name,
            "Score": f"{a.relevance_score:.1f}",
            "Status": status_display,
        }
        data.append(row)

    df = pd.DataFrame(data)

    # Add CSS to style the custom table
    st.markdown(
        """
            <style>
            .results-table-header {
                display: grid;
                grid-template-columns: 1.2fr 1.5fr 2.5fr 1.8fr 1.5fr 1fr 1.2fr;
                gap: 1rem;
                padding: 1rem;
                background: rgba(30, 41, 59, 0.5);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px 8px 0 0;
                font-weight: 600;
                color: #94A3B8;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0;
            }
            
            .results-table-row {
                display: grid;
                grid-template-columns: 1.2fr 1.5fr 2.5fr 1.8fr 1.5fr 1fr 1.2fr;
                gap: 1rem;
                padding: 1rem;
                align-items: center;
                transition: all 0.2s ease;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                background: rgba(30, 41, 59, 0.3);
                margin-bottom: 0.75rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            }
            
            .results-table-row:hover {
                background: rgba(0, 180, 216, 0.08);
                border-color: rgba(0, 180, 216, 0.4);
                box-shadow: 0 4px 12px rgba(0, 180, 216, 0.15);
                transform: translateY(-2px);
            }
            
            .results-table-container {
                display: flex;
                flex-direction: column;
                flex-grow: 1;
                min-height: 200px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                overflow-y: auto;
                background: rgba(30, 41, 59, 0.3);
            }                

            """,
        unsafe_allow_html=True,
    )

    # Display table header
    st.markdown(
        """
            <div class="results-table-header">
                <div>Lens ID</div>
                <div>Patent #</div>
                <div>Title</div>
                <div>Inventor(s)</div>
                <div>Jurisdiction</div>
                <div>Score</div>
                <div>Status</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

    # Display table rows with hover effect
    results_container = st.container()
    with results_container:
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.2, 1.5, 2.5, 1.8, 1.5, 1, 1.2])
        
        for idx, row in df.iterrows():
            lens_id = row["Lens ID"]
            
            # Create HTML row with hover effect
            row_html = f"""
            <div class="results-table-row">
                <div>Placeholder</div>
                <div>{row["Patent #"]}</div>
                <div>{row["Title"]}</div>
                <div>{row["Inventor(s)"]}</div>
                <div>{row["Jurisdiction"]}</div>
                <div style="text-align: center;">{row["Score"]}</div>
                <div>{row["Status"]}</div>
            </div>
            """
            st.markdown(row_html, unsafe_allow_html=True)
            
            # Handle button clicks via session state (displayed above the row)
            if st.button("LOAD", key=f"lens_btn_{idx}_{lens_id}", use_container_width=True):
                st.session_state["selected_lens_id_for_analysis"] = lens_id
