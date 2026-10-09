"""Shared Employee hierarchy graph checks for the chart and mutations."""

from collections import defaultdict, deque


def cyclic_employee_ids(employee_ids, relationships):
    """Return the IDs left in a graph after topological traversal."""
    indegree = {employee_id: 0 for employee_id in employee_ids}
    children = defaultdict(list)
    for superior_id, employee_id in relationships:
        children[superior_id].append(employee_id)
        indegree[employee_id] += 1
    queue = deque(employee_id for employee_id, degree in indegree.items() if degree == 0)
    while queue:
        for child_id in children[queue.popleft()]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)
    return sorted(employee_id for employee_id, degree in indegree.items() if degree)


def would_create_cycle(superior_id, employee_id, relationships):
    pairs = set(relationships)
    pairs.add((superior_id, employee_id))
    employee_ids = {identity for pair in pairs for identity in pair}
    return bool(cyclic_employee_ids(employee_ids, pairs))
