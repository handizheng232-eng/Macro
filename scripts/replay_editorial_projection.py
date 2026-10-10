"""Pure reviewed-editorial projection; file admission remains caller-owned."""
from copy import deepcopy
import re

SECTION_FIELDS = ('id', 'title', 'judgement', 'expectation', 'reality', 'mechanism', 'divergence', 'implication', 'validation', 'sourceIds', 'reportIds')
ENTRY_FIELDS = ('id', 'date', 'title', 'text', 'sourceIds', 'reportIds', 'evidenceRefs', 'dateNote', 'claimType', 'dateRole', 'analysisAsOf', 'firstAvailableDate', 'historicalAsOfEligible', 'retrospectiveOnly', 'latePublishedInterpretation')
LOCATOR_FIELDS = ('id', 'reportId', 'actor', 'publicationDate', 'locatorLabel', 'evidenceBasis')
SOURCE_FIELDS = ('id', 'title', 'publisher', 'url', 'date', 'kind', 'status', 'note', 'sourceSHA256', 'firstAvailableDate', 'historicalAsOfEligible', 'retrospectiveOnly')


def project_editorial(base, study, framework, public_locators, admitted_reference_ids, *, source_admissions=()):
    """Attach selected display fields, leaving baseline evidence unchanged."""
    result = deepcopy(base)
    themes = [s['id'] for s in study['sections']]
    if themes != [s['id'] for s in base['marketAnalysis']['sections']] or set(themes) != set(framework['byTopicId']):
        raise ValueError('editorial theme identity or order changed')
    for cards in framework['byTopicId'].values():
        for card in cards:
            if card.get('retrospectiveOnly') is not True or any(o.get('historicalAsOfEligible') is not False for s in card['series'] for o in s['observations']):
                raise ValueError('framework auxiliary values must remain retrospective, not historical vintages')
    for source in source_admissions:
        selected = {k: deepcopy(source[k]) for k in SOURCE_FIELDS if k in source}
        if selected.get('date') is None:
            selected['date'] = ''
        selected['status'] = selected.get('status') or '当前追溯补充；历史资格未核'
        result['sources'].append(selected)
    registered = {'sourceIds': {s['id'] for s in result['sources']}, 'reportIds': {r['id'] for r in result['reports']}, 'evidenceRefs': set(admitted_reference_ids)}
    citation_map = {str(row['number']): row['sourceId'] for row in study.get('citationSources', [])}
    sections = []
    for raw in study['sections']:
        section = {k: deepcopy(raw[k]) for k in SECTION_FIELDS if k in raw}
        section['deepDive'] = {}
        for role, entries in raw['deepDive'].items():
            projected = []
            for entry in entries:
                if entry.get('historicalAsOfEligible') is not False or entry.get('firstAvailableDate') is not None:
                    raise ValueError('current editorial research cannot promote historical availability')
                for field, allowed in registered.items():
                    unknown = set(entry[field]) - allowed
                    if unknown:
                        raise ValueError(f'unregistered {field}: {sorted(unknown)}')
                item = {k: deepcopy(entry[k]) for k in ENTRY_FIELDS if k in entry}
                item['text'] = re.sub(r'\[(\d+)\]', lambda m: '[' + citation_map.get(m[1], m[1]) + ']', item['text'])
                item['supportingEvidence'] = [{k: deepcopy(public_locators[ref][k]) for k in LOCATOR_FIELDS if k in public_locators[ref]} for ref in item['evidenceRefs'] if ref in public_locators]
                projected.append(item)
            section['deepDive'][role] = sorted(projected, key=lambda item: item.get('date') or '9999') if role.endswith('Timeline') else projected
        section['frameworkEvidence'] = deepcopy(framework['byTopicId'][raw['id']])
        sections.append(section)
    result['marketAnalysis'] = {k: deepcopy(study[k]) for k in ('title', 'conclusion', 'limitations')}
    result['marketAnalysis']['sections'] = sections
    return result


def apply_summaries(base, summaries):
    """Apply a display-only summary layer to already admitted research."""
    if any(summaries.get(key) != base.get(key) for key in ('startDate', 'asOf')):
        raise ValueError('summary window differs from admitted research')
    if [s['id'] for s in summaries['sections']] != [s['id'] for s in base['marketAnalysis']['sections']]:
        raise ValueError('summary theme identity or order differs')
    result = deepcopy(base)
    by_id = {s['id']: s for s in summaries['sections']}
    sources = {s['id'] for s in base['sources']}
    reports = {r['id'] for r in base['reports']}

    def validate(summary, entries):
        if not summary['evidenceRefs'] or not set(summary['evidenceRefs']) <= {e['id'] for e in entries}:
            raise ValueError('summary must reference admitted nodes in this topic and aspect')
        if not set(summary['sourceIds']) <= sources or not set(summary['reportIds']) <= reports:
            raise ValueError('summary source or report is unregistered')

    for section in result['marketAnalysis']['sections']:
        overlay = by_id[section['id']]
        validate(overlay['periodSummary'], [e for entries in section['deepDive'].values() for e in entries])
        if set(overlay['aspectSummaries']) != set(section['deepDive']):
            raise ValueError('summary aspects differ from admitted analytical aspects')
        period = {k: deepcopy(overlay['periodSummary'][k]) for k in ('paragraphs', 'sourceIds', 'reportIds', 'evidenceRefs')}
        period.update(retrospectiveOnly=True, historicalAsOfEligible=False)
        section['periodSummary'] = period
        section['aspectSummaries'] = {}
        for role, summary in overlay['aspectSummaries'].items():
            validate(summary, section['deepDive'][role])
            item = {k: deepcopy(summary[k]) for k in ('text', 'sourceIds', 'reportIds', 'evidenceRefs')}
            item.update(retrospectiveOnly=True, historicalAsOfEligible=False)
            section['aspectSummaries'][role] = item
    return result
