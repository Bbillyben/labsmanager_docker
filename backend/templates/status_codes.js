{% load customs_tags %}
{% for items in codes %}
    const {{items.name}}_codes = {
        {% for item in items.data %}
        '{{ forloop.counter0 }}':{
            key: '{{ item.key }}',
            value: '{{ item.value }}', 
            {% if item.num_parent %}prefix:"┝{% for inc in item.num_parent|get_range %}━{% if not forloop.last %}┅{%endif%}{% endfor %}"{% endif%}
        },
        {% endfor %}
    };
{% endfor %}
