# AroundMe Agent

A sophisticated AI-powered location discovery platform that combines multiple data sources to provide real-time insights about interesting places, events, and activities in any city or YOUR current city(based off of your location). Built with modern AI agents, web scraping, and interactive mapping.

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

The system uses **LangGraph/LangChain** to orchestrate complex AI workflows that can adapt and make intelligent decisions in real-time. Each data source is processed through specialized AI agents:

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
   - **Enhanced Event Detection**: Uses 8 targeted search queries for events, openings, festivals, and "things to do"
   - **Opening & Launch Tracking**: Specifically searches for new restaurant openings, business launches, and grand openings
   - **Activity Discovery**: Focuses on local activities, attractions, and entertainment venues
   - **LLM Location Extraction**: Uses GPT-4 to extract real locations from news articles
   - **Content Filtering**: Prioritizes lifestyle and entertainment content over business news
   - **Temporal Relevance**: Prioritizes recent events and upcoming activities with date-based scoring


### Intelligent Geocoding Pipeline

The geocoding system uses a 5-stage fallback (this is the exact order implemented in code):

```
Stage 1: Serper Knowledge Graph (pulls address directly when available)
    ↓ (if not found)
Stage 2: Site-specific Serper searches (Google Maps / Yelp / YellowPages / Facebook / OpenTable) 
           + HTML scraping with BeautifulSoup + address extraction
    ↓ (if still unresolved)
Stage 3: LLM ranking of candidate addresses using GPT-4
    ↓ (if still unresolved)
Stage 4: Google Places API (FindPlaceFromText)
    ↓ (if still unresolved)
Stage 5: OpenStreetMap (Nominatim) text search
```

Each geocoding attempt includes:
- **City boundary validation** using Mapbox API to ensure coordinates are within target area
- **LLM-assisted address ranking** (in Stage 3) to select the most relevant result from candidate addresses
- **HTML scraping** from 6 different platforms for address extraction
- **Regex pattern matching** for address validation
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
- **Enhanced News APIs**: Events, openings, festivals, and "things to do" with LLM location extraction
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

SERPER_API_KEY=your_serper_api_key
GOOGLE_PLACES_API_KEY=your_google_places_api_key
NEWS_API_KEY=your_news_api_key
TICKETMASTER_API_KEY=your_ticketmaster_api_key

# Set up LangSmith for tracking
LANGSMITH_TRACING=
LANGSMITH_ENDPOINT=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=

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

Built with modern AI technologies and best practices for scalable, maintainable code.