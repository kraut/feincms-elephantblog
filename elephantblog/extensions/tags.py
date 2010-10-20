from feincms.contrib.django_tagging import tag_model




def register(cls, admin_cls, *args):    

    tag_model(cls, admin_cls, select_field=True)
    
