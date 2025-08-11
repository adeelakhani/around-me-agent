"""
Search terms for Reddit scraping
"""
import random

def get_search_terms(city: str) -> list:
    """Get optimized search terms for Reddit scraping"""
    # Natural search terms that sound like how people actually talk
    search_terms = [
        f"cool%20places%20{city.lower()}",
        f"fun%20things%20to%20do%20{city.lower()}",
        f"best%20places%20{city.lower()}",
        f"hidden%20gems%20{city.lower()}",
        f"underrated%20places%20{city.lower()}",
        f"unique%20places%20{city.lower()}",
        f"interesting%20spots%20{city.lower()}",
        f"local%20favorites%20{city.lower()}",
        f"must%20see%20{city.lower()}",
        f"favorite%20spots%20{city.lower()}",
        f"amazing%20places%20{city.lower()}",
        f"cool%20spots%20{city.lower()}"
    ]
    
    return search_terms

def get_random_search_term(city: str) -> str:
    """Get a random search term for the given city"""
    search_terms = get_search_terms(city)
    return random.choice(search_terms)
