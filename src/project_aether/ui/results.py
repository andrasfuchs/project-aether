import streamlit as st
import pandas as pd


def render_results_tab(assessments, jurisdiction_map):
    st.markdown("### Search Results")

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
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                align-items: center;
                transition: background-color 0.2s ease;
            }
            
            .results-table-row:hover {
                background: rgba(0, 180, 216, 0.05);
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
            </style>
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

    # Display table rows with clickable Lens ID buttons
    results_container = st.container()
    with results_container:
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1.2, 1.5, 2.5, 1.8, 1.5, 1, 1.2])

            with col1:
                lens_id = row["Lens ID"]
                if st.button(lens_id, key=f"lens_btn_{idx}_{lens_id}", use_container_width=True):
                    st.session_state["selected_lens_id_for_analysis"] = lens_id

            with col2:
                st.write(row["Patent #"])

            with col3:
                st.write(row["Title"])

            with col4:
                st.write(row["Inventor(s)"])

            with col5:
                st.write(row["Jurisdiction"])

            with col6:
                # Display score as a mini progress bar with percentage
                score_val = float(row["Score"])
                st.progress(score_val / 100, text=f"{row['Score']}%")

            with col7:
                st.write(row["Status"])
