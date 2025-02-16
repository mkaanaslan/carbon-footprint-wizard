# Carbon Footprint Wizard 🌱

The Carbon Footprint Wizard is an interactive tool that helps users calculate and understand the environmental impact of their recipes and meals. By leveraging multiple life cycle assessment (LCA) databases and advanced natural language processing, it provides detailed carbon footprint analyses of ingredients and cooking processes.

## Usage

1. Enter your recipe with ingredients and quantities in natural language
2. Select the target country for analysis
3. Choose matching products for each ingredient from the suggestions
4. Review the detailed carbon footprint analysis
5. Use the chat interface to explore specific aspects of the analysis

## Setup

1. Clone the repository and run the main script:
```bash
git clone https://github.com/mkaanaslan/carbon-footprint-wizard.git
cd carbon-footprint-wizard
python main.py
```

2. On first run, you'll be prompted to enter your OpenAI API key. The key will be saved in `openai_key.txt` for future use.

The application will then go through several initialization steps:

1. **Data Processing** (takes time):
   - Downloads BONSAI database files (footprints, recipes, locations, activity names)
   - Downloads and processes Agribalyse data
   - Downloads and processes Big Climate Database data

2. **Vector Database Setup**:
   - Downloads the sentence transformer model (all-MiniLM-L6-v2)
   - Creates vector embeddings for all products
   - Builds FAISS indices for efficient similarity search

After these steps complete, the Gradio interface will launch and you can start using the application. Note that the initialization process only happens on first run - subsequent launches will use the downloaded data and created indices.

## Project Structure

- `main.py`: Application entry point and UI setup
- `data_handler.py`: Database interaction and data processing
- `data_preprocessing.py`: Database setup and preprocessing
- `extraction.py`: Natural language processing for ingredient extraction
- `llm_loop.py`: Chat interface and result generation
- `product_search.py`: Semantic search implementation

## Data Sources

The system integrates data from three major environmental impact databases:
- BONSAI
- Agribalyse
- Big Climate Database

## License

[Add your chosen license]

## Contributors

[Add contributor information]

## Citation

If you use this tool in your research, please cite:
[Add citation information]

## Acknowledgments

This project utilizes several open databases and tools:
- BONSAI database
- Agribalyse database
- Big Climate Database
- Sentence Transformers
- FAISS
- OpenAI GPT-4o-mini

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
