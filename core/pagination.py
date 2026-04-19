import math

from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

def do_pagination(result, count, page=1, page_size=3, encryption_fields=None, context=None):
    '''
    Paginates the given result and returns the result dictionary
    '''
    total_pages = math.ceil(count / page_size) if count != 0 else 1
    page_ids = list(range(1, total_pages + 1))
    current_page = page

    result = {
        'page_ids': page_ids,
        'current_page': current_page,
        'next_page_id': current_page + 1 if current_page < total_pages else None,
        'total_pages': total_pages,
        'total_results': count,
        'page_size': page_size,
        'results': result
    }
    if context:
        result.update(context)
    return result

