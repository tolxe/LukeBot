import os

import requests
from datetime import datetime, timedelta

token = os.getenv('GG_TOKEN')
headers = {'Authorization': f'Bearer {token}'}

# Luke's Start GG Info
# Slug (changes with the tag)
# user/e4082a74
ID = 1116942

endpoint = "https://api.start.gg/gql/alpha"


def get_gamer_tag() -> str:
    """Fetches Luke's current Start.GG Epic Gamer Tag"""
    query = '''
    query Luke($id: ID){
    user(id: $id){
        id,
        slug,
        player{
            gamerTag
            }
        }
    }
    '''

    raw_response = requests.post(endpoint, json={'query': query, 'variables': {'id': ID}}, headers=headers)
    json = raw_response.json()
    tag = json['data']['user']['player']['gamerTag']
    return tag


def get_last_result(num_results: int, gamertag: str):
    """Returns the last N results from Luke's profile"""
    query = '''
    query LastResult($id: ID){
    user(id: $id){
        events(query:{
          perPage: %d,
          page:1
        }) {
          nodes {
            tournament {
              name
              id
              shortSlug
            }
            name
            numEntrants
            state
            standings(query:{
              perPage: %d,
              page:1
              filter:{
                search:{
                  searchString:"%s"
                }
                }
              }) {
              nodes {
                placement
                isFinal
              }
            }
          }
        }
    }
    }
    ''' % (num_results, num_results, gamertag)
    raw_response = requests.post(endpoint, json={'query': query, 'variables': {'id': ID}}, headers=headers)
    response = raw_response.json()
    return response['data']['user']['events']['nodes']


def get_upcoming_tournaments(id_: int, gamertag: str):
    query = '''
    query Upcoming($id: ID){
    user(id: $id){
        tournaments(query: {
            perPage: 5,
            page: 1,
            filter: {
                upcoming:true
            }
        }){
            nodes{
                name
                id
                shortSlug
                startAt
                state
                events(limit:3){
                  id
                  name
                  entrants(query:{filter:{name:"%s"}}){
                    nodes{
                      id
                    }
                  }
                }
            }
        }
    }
    }
    ''' % gamertag
    raw_response = requests.post(endpoint, json={'query': query, 'variables': {'id': id_}}, headers=headers)
    response = raw_response.json()
    return response['data']['user']['tournaments']['nodes'][::-1]


def process_results(response):
    """Processes list of Finalised Tournament Objects into a readable Format"""
    results = ""
    for event in response:
        results += f"Tournament - `{event['tournament']['name']}`"
        slug = event['tournament']['shortSlug']
        if slug:
            results += f" - [Start.GG]((https://start.gg/{event['tournament']['shortSlug']}))"
        results += "\n"

        results += f"PROGRESS : `{event['state']}`\n"
        placing = event['standings']['nodes'][0]['placement']
        results += f"Placement : `{placing}` in `{event['numEntrants']}`\n\n"

    return results


def process_upcoming(response):
    """Processes list of Upcoming Tournament Objects into a readable format"""
    results = ""
    for event in response:
        results += f"Tournament - `{event['name']}`"
        slug = event['shortSlug']
        if slug:
            results += f" - [Start.GG](https://start.gg/{event['shortSlug']})"
        results += "\n"
        event_start = datetime.utcfromtimestamp(event['startAt'])
        event_starts_in = event_start - datetime.utcnow()
        days, hours, minutes = event_starts_in.days, event_starts_in.seconds // 3600, event_starts_in.seconds // 60 % 60
        if event_starts_in < timedelta():
            results += f"Started `{abs(days)}` days, `{hours}` hours, `{minutes}` minutes ago\n"
            event_id = event['id']
            entrant_id = -1
            for events in event['events']:
                if 'single' in events['name'].lower() and events['entrants']['nodes']:
                    entrant_id = events['entrants']['nodes'][0]['id']
                    event_id = events['id']
                    break
            set_scores = ongoing_results(event_id, entrant_id)
            results += "Set Scores -\n"
            for set_result in set_scores:
                results += f"`{set_result['fullRoundText']}` -\n"
                if set_result['displayScore']:
                    results += f"{set_result['displayScore']}\n"

        else:
            results += f"Begins in `{days}` days, `{hours}` hours, `{minutes}` minutes\n"
    return results


def ongoing_results(event_id: int, entrant_id: int):
    query = '''
    query InProgressResults($event_id: ID, $entrant_id: ID){
    event(id: $event_id){
        tournament{
            name
        }
        name
        sets(filters:{entrantIds:[$entrant_id]}){
            nodes{
                fullRoundText
                displayScore
                slots{
                    entrant{
                        id
                        name
                    }
                }
            }
        }
        }
    }
    '''
    raw_response = requests.post(
        endpoint, json={'query': query, 'variables': {'event_id': event_id, 'entrant_id': entrant_id}}, headers=headers
    )
    response = raw_response.json()
    event = response['data']['event']
    if event is not None:
        current_results = event['sets']['nodes'][::-1]
    else:
        current_results = []
    return current_results


def check_luke():
    results = ""
    gamertag = get_gamer_tag()
    last_result = get_last_result(1, gamertag)
    upcoming = get_upcoming_tournaments(ID, gamertag)
    results += f"**Current Luke Tag** - `{gamertag}`\n"
    results += "Last Result:\n"
    results += process_results(last_result)
    results += f"Upcoming `{len(upcoming)}` Tournaments - \n"
    results += process_upcoming(upcoming)
    return results
