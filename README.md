# AroundMe Agent

A sophisticated AI-powered location discovery platform that combines multiple data sources to provide real-time insights about interesting places, events, and activities in any city. Built with modern AI agents, web scraping, and interactive mapping.

## Overview

AroundMe Agent is a full-stack web application that discovers and visualizes Points of Interest (POIs) by aggregating data from multiple sources:

- **Reddit Community Recommendations** - AI-powered scraping of community discussions
- **Local News & Events** - Current events and openings
- **Municipal Services** - 311 service requests and city data
- **Event Discovery** - Upcoming activities and gatherings

The platform uses advanced AI agents with LangGraph workflows, browser automation, and sophisticated geocoding to provide accurate, real-time location data with rich context.

## How It Works

AroundMe Agent employs a sophisticated multi-layered architecture that combines cutting-edge AI technologies with real-time data processing to deliver intelligent location insights.

### AI Agent Orchestration

The system uses **LangGraph** to orchestrate complex AI workflows that can adapt and make intelligent decisions in real-time. Each data source is processed through specialized AI agents:

1. **Reddit Community Intelligence Agent**
   - Navigates Reddit using browser automation (Playwright)
   - Analyzes community discussions with GPT-4 for sentiment and context
   - Extracts place recommendations with structured output validation
   - Identifies authentic user experiences vs. generic mentions

2. **Municipal Services Intelligence Agent**
   - **Dynamic Portal Discovery**: Automatically finds city data portals using web search and pattern matching (CKAN, Socrata, Open311)
   - **Intelligent Data Fetching**: Downloads and parses JSON/CSV files with encoding detection and ZIP extraction
   - **LLM Coordinate Inference**: When coordinates are missing, uses GPT-4 to infer lat/lng from addresses, intersections, or postal codes
   - **Real-time Service Mapping**: Converts 311 requests into map POIs showing infrastructure issues, community concerns, and local developments

3. **News & Events Discovery Agent**
   - Aggregates data from multiple news APIs and event platforms
   - Performs temporal analysis to prioritize recent and upcoming events
   - Extracts location-specific context and relevance scoring


### Intelligent Geocoding Pipeline

The geocoding system uses a staged fallback (this is the exact order implemented in code):

```
Primary: Serper Knowledge Graph (pulls address directly when available)
    ↓ (if not found)
Secondary: Site-specific Serper searches (Google Maps / Yelp / YellowPages / Facebook) 
           + HTML scraping with BeautifulSoup + LLM ranking of candidate addresses
    ↓ (if still unresolved)
Tertiary: Google Places API (FindPlaceFromText)
    ↓ (if still unresolved)
Quaternary: OpenStreetMap (Nominatim) text search
```

Each geocoding attempt includes:
- **City boundary validation** using Mapbox API to ensure coordinates are within target area
- **LLM-assisted address ranking** (only in Step 2) to select the most relevant result from candidate addresses
- **Multiple provider strategies** before giving up (returns `None` on total failure)

### Real-Time Data Processing

The system processes data through multiple stages:

1. **Content Extraction**: Browser automation extracts raw content from dynamic websites
2. **AI Analysis**: GPT-4 analyzes content for relevance, sentiment, and context
3. **Structured Output**: Pydantic models ensure type safety and data validation
4. **Geocoding**: Multi-source coordinate resolution with validation

### Stateful Workflow Management

LangGraph manages complex state transitions that allow the system to:
- **Adapt to failures** and retry with alternative strategies
- **Maintain context** across multiple processing steps
- **Make intelligent routing decisions** based on data quality and availability
- **Handle partial failures** gracefully without losing progress

### Frontend Intelligence

The frontend implements sophisticated real-time features:
- **3D building renderings** with custom Mapbox styling
- **Real-time filtering** with instant visual feedback
- **Interactive popups** that display POI information
- **Recent activity tracking** with intelligent deduplication

### Data Quality Assurance

Every POI undergoes rigorous validation:
- **Source verification** to ensure data authenticity
- **Coordinate validation** to prevent out-of-bounds locations
- **Content filtering** to remove spam and irrelevant mentions
- **Temporal relevance** scoring for time-sensitive information

This architecture enables the system to provide highly accurate, contextually relevant location intelligence that adapts to user needs and data availability in real-time.

## Architecture

### Frontend
- **Next.js 15** with TypeScript and React 19
- **Mapbox GL** for interactive 3D mapping
- **Tailwind CSS** for modern, responsive UI


### Backend
- **FastAPI** for high-performance REST API
- **LangGraph/LangChain** for AI agent workflows
- **Playwright** for browser automation
- **OpenAI GPT-4** for content analysis


### AI Agents
- **Stateful workflows** with conditional routing
- **Browser automation** for dynamic content scraping
- **Structured output** with Pydantic models
- **Context-aware** content extraction and analysis

## Features

### Interactive Mapping
- 3D building renderings with custom Mapbox styles
- POI filtering
- Location popups with rich context and sharing
- Recent activity tracking and history

### AI-Powered Discovery
- Intelligent Reddit content scraping and analysis
- Context-aware place extraction from community discussions
- Multi-source geocoding with validation
- Sentiment analysis for recommendation quality

### Data Sources
- **Reddit**: Community recommendations and discussions
- **News APIs**: Current events and local happenings
- **311 Services**: Municipal service requests and issues
- **Event APIs**: Upcoming activities and gatherings

### Advanced Geocoding
- Multi-API fallback system (OpenStreetMap, Google Places, Serper)
- Address validation and city boundary checking
- LLM-assisted address ranking and selection
- Coordinate accuracy validation

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **OpenAI API Key** - Required for AI agents and content analysis
- **Mapbox Access Token** - Required for geocoding and location services
- **Serper API Key** - Enhanced geocoding and search capabilities
- **Google Places API Key** - Enhanced geocoding and place details
- **News API Key** - News and events aggregation
- **Ticketmaster API Key** - Event discovery and ticketing

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aroundme-agent
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```bash
cd client

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your Mapbox token
```

### 4. Environment Variables

Create `.env` in the backend directory:

```env
# Required
OPENAI_API_KEY=your_openai_api_key
MAPBOX_ACCESS_TOKEN=your_mapbox_access_token

# Optional (for enhanced functionality)
SERPER_API_KEY=your_serper_api_key
GOOGLE_PLACES_API_KEY=your_google_places_api_key
NEWS_API_KEY=your_news_api_key
TICKETMASTER_API_KEY=your_ticketmaster_api_key

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

Create `.env.local` in the client directory:

```env
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token
```

## Usage

### Development

#### Start Backend Server

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

#### Start Frontend Development Server

```bash
cd client
npm run dev
```

The application will be available at `http://localhost:3000`

### Production

#### Build Frontend

```bash
cd client
npm run build
npm start
```

#### Deploy Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

## API Documentation

### Endpoints

#### GET `/api/locations`

Retrieve Points of Interest for a specific location.

**Parameters:**
- `lat` (float): Latitude coordinate
- `lon` (float): Longitude coordinate

**Response:**
```json
[
  {
    "name": "Pizza Place",
    "lat": 43.6532,
    "lng": -79.3832,
    "summary": "Great pizza with authentic Italian style",
    "type": "reddit",
    "radius": 20
  }
]
```

### Data Types

- **reddit**: Community recommendations from Reddit
- **news**: Current events and local news
- **event**: Upcoming events and activities
- **311_service**: Municipal service requests

## Project Structure

```
aroundme-agent/
├── backend/
│   ├── agents/
│   │   ├── reddit_scraper.py      # LangGraph Reddit scraping agent
│   │   ├── news_scraper.py        # News aggregation agent
│   │   ├── municipal_api_discovery.py  # 311 services agent
│   │   └── data_portal_discovery.py    # Data portal agent
│   ├── reddit/
│   │   ├── models.py              # Pydantic data models
│   │   ├── geocoding.py           # Multi-source geocoding
│   │   ├── url_extraction.py      # URL extraction utilities
│   │   └── search_terms.py        # Search term management
│   ├── routes/
│   │   └── locations.py           # API endpoints
│   ├── utils/
│   │   └── location.py            # Location utilities
│   ├── tests/                     # Test files
│   ├── server.py                  # FastAPI application
│   └── requirements.txt           # Python dependencies
├── client/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx           # Main application component
│   │       ├── layout.tsx         # Application layout
│   │       └── globals.css        # Global styles
│   ├── public/                    # Static assets
│   ├── package.json               # Node.js dependencies
│   └── next.config.ts             # Next.js configuration
└── README.md                      # This file
```

## AI Agent Workflows

### Reddit Scraper Agent

The Reddit scraper uses a sophisticated LangGraph workflow:

1. **scrape_reddit_node**: Navigate to Reddit and extract content using browser automation
2. **tools_node**: Execute browser tools (navigation, text extraction)
3. **extract_pois_node**: Analyze content with AI to find places mentioned
4. **geocode_pois_node**: Get coordinates for each discovered place

**State Flow:**
```
Initial State → Scrape Reddit → Extract POIs → Geocode → Final Results
```

### Key Features

- **Conditional Routing**: Smart workflow decisions based on AI analysis
- **Browser Automation**: Real-time web scraping with Playwright
- **Structured Output**: Type-safe data with Pydantic models
- **Multi-source Geocoding**: Fallback strategies for location accuracy

## Development

### Adding New Data Sources

1. Create a new agent in `backend/agents/`
2. Implement the LangGraph workflow
3. Add the data source to `backend/routes/locations.py`
4. Update the frontend to handle the new data type

### Extending Geocoding

The geocoding system supports multiple providers:

```python
# Add new geocoding provider
def geocode_with_new_provider(poi_name: str, city: str) -> Optional[Dict]:
    # Implementation
    pass

# Integrate into fallback system
coords = geocode_with_fallback(poi_name, city, province, country)
```

### Customizing the Map

The frontend uses Mapbox GL with custom styling:

```typescript
// Custom map style
const mapStyle = 'mapbox://styles/your-username/your-style-id'

// Custom markers
const markerEl = document.createElement('div')
markerEl.style.background = `radial-gradient(...)`
```

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/
```

### Frontend Tests

```bash
cd client
npm test
```

### Manual Testing

1. Start both servers
2. Navigate to `http://localhost:3000`
3. Click on map markers to test recent activity
4. Use filters to test different data types
5. Check browser console for debug information

## Performance Considerations

### Backend Optimization

- **Async Operations**: All I/O operations are asynchronous
- **Caching**: Implement Redis for API response caching
- **Rate Limiting**: Add rate limiting for external APIs
- **Connection Pooling**: Use connection pools for database operations

### Frontend Optimization

- **Code Splitting**: Next.js automatic code splitting
- **Image Optimization**: Next.js automatic image optimization
- **Bundle Analysis**: Use `npm run build` to analyze bundle size
- **Lazy Loading**: Implement lazy loading for map components

## Deployment

### Docker Deployment

```dockerfile
# Backend Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Frontend Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

### Environment-Specific Configuration

- **Development**: Use `.env.local` for local development
- **Staging**: Use environment variables in deployment platform
- **Production**: Use secure environment variable management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow TypeScript best practices
- Use Pydantic for data validation
- Implement comprehensive error handling
- Add tests for new features
- Update documentation for API changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **LangGraph** for AI workflow orchestration
- **Playwright** for browser automation
- **Mapbox** for mapping services
- **OpenAI** for AI capabilities
- **FastAPI** for high-performance API framework

## Support

For support and questions:

- Create an issue in the repository
- Check the documentation in `/docs`
- Review the test files for usage examples

---

Built with modern AI technologies and best practices for scalable, maintainable code.
