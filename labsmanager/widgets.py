from django import forms
from django.utils.safestring import mark_safe

class CustomCheckBox(forms.CheckboxInput):
    template_name = 'django/forms/widgets/checkbox.html'
    def __init__(self, attrs=None):
        super().__init__(attrs)
        # On ajoute un attribut de classe par défaut dans le dictionnaire attrs
        default_attrs = {'class': 'custom-checkbox-LM'}
        
        # Si on passe des attributs supplémentaires, on les combine avec les défauts
        if attrs:
            default_attrs.update(attrs)
        
        self.attrs = default_attrs
        
        
    def render(self, name, value, attrs=None, renderer=None):
        # Utilisation de la méthode render héritée pour garantir un rendu correct
        return super().render(name, value, attrs, renderer)


    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # Tu peux ajouter des arguments personnalisés ici si tu en as besoin
    #     self.custom_attr = kwargs.get('custom_attr', 'default_value')

    # def render(self, name, value, attrs=None, renderer=None):
    #     # Rendu HTML personnalisé du widget
    #     final_attrs = self.build_attrs(attrs)
    #     final_attrs['class'] = 'custom-widget-class'  # Ajoute des classes CSS ou d'autres attributs si besoin
        
    #     # Le HTML personnalisé que tu veux rendre
    #     html = f'<div class="custom-widget-container">{self.get_custom_html(value, final_attrs)}</div>'
        
    #     return mark_safe(html)

    # def get_custom_html(self, value, attrs):
    #     # Cette méthode génère le HTML spécifique que tu veux pour ton champ
    #     return f'<input class="custom-cb-form" type="checkbox" name="{attrs.get("name")}" value="{value}" {self.flatatt(attrs)} />'
    
    # def render(self, name, value, attrs=None, renderer=None):
    #     # Construction des attributs HTML
    #     final_attrs = self.build_attrs(attrs)
        
    #     # Si la valeur est vraie (case cochée), on ajoute l'attribut `checked`
    #     checked = 'checked' if value else ''
        
    #     # Crée le HTML personnalisé
    #     html = f'<input class ="custom-cb" type="checkbox" name="{name}" value="1" {checked} '
        
    #     # Ajouter les attributs supplémentaires générés par build_attrs
    #     for key, val in final_attrs.items():
    #         html += f'{key}="{val}" '
        
    #     # Fermer la balise input
    #     html += '/>'
        
    #     return mark_safe(html)


