from textwrap import dedent

AI_GENERATED_NOTICE_MD = dedent("""
    > **AI-generated documentation notice**
    >
    > This documentation was generated with the assistance of an AI system using Tableau workbook metadata.
    > It reflects the structure and logic present in the source file at the time of generation and does not validate business intent, analytical correctness, or data quality.
    > Dashboard owners remain responsible for review and approval.
""").lstrip()
