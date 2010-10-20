from datetime import date

from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from feincms.translations import short_language_code
# from tagging.models import Tag, TaggedItem
from django.core.exceptions import FieldError

from feincms.views.generic import list_detail
from feincms.views.decorators import *

from models import Entry, Category
import settings


def entry(request, year, month, day, slug, language_code=None, **kwargs):
    context={}

    entry = get_object_or_404(Entry.objects.select_related(), 
                              published_on__year=year,
                               published_on__month=month,
                               published_on__day=day,
                               slug=slug)

    
    if not entry.isactive() and not request.user.is_authenticated():
        raise Http404
    else:
        extra_contest = {'entry':entry, 
                         'date': date(int(year), int(month),int(day)),
                         'comments' : settings.BLOG_COMMENTS
                         }
        # Needed if its used as ApplicationContext:
        # Than you can specify a different template for using it as AppContent
        # or using it standalone.
        template_name = kwargs.get('template_name')
        template = 'blog/entry_detail.html'
        if template_name:
            template = template_name
        return render_to_response(template, extra_contest, 
                                  context_instance=RequestContext(request))

""" Date views use object_list generic view due to pagination """
def entry_list(request, category=None, year=None, month=None, day=None, page=0, 
               paginate_by=10, template_name='blog/entry_list.html', limit=None,
               language_code=None, **kwargs):
    
    extra_context = getattr(kwargs, 'extra_context', {}) 
    if language_code:
        queryset = Entry.objects.active().filter(language=language_code)
    else:
        try:
            language_code = request._feincms_page.language
            queryset = Entry.objects.active().filter(language=language_code)
        except (AttributeError, FieldError):
            queryset = Entry.objects.active()
    if limit:
        queryset = queryset[:limit]
    if category:
        queryset = queryset.filter(categories__translations__slug=category)
        extra_context.update({'category': category})
    if year:
        queryset = queryset.filter(published_on__year=int(year))
        extra_context.update({'drilldown_mode': 'year', 'title' : _('entries of the year')})
    else:
        year=1
    if month:
        queryset = queryset.filter(published_on__month=int(month))
        extra_context.update({'drilldown_mode': 'month', 'title' : _('entries of the month')})
    else:
        month=1
    if day:
        queryset = queryset.filter(published_on__day=int(day))
        extra_context.update({'drilldown_mode': 'day', 'title' : _('entries of the year')})
    else:
        day=1
    
    extra_context.update({'date':date(int(year), int(month), int(day)),
                          'comments' : settings.BLOG_COMMENTS})

    if settings.BLOG_LIST_PAGINATION:
        paginate_by = settings.BLOG_LIST_PAGINATION
    return list_detail.object_list(
      request,
      queryset = queryset,
      paginate_by = paginate_by,
      #page = page,
      template_name = template_name,
      extra_context = extra_context,
      **kwargs)
   
def browse_entries(request, category_name='', year=None, month=None, day=None, page=0, 
               paginate_by=10, template_name='blog/category_list.html', 
               entry_template_name= 'blog/entry_list.html', limit=None,
               language_code=None, **kwargs):
    '''  
        Lets the user browse through the hierarchically blog categieres.
        Entry list is shown only if the category to show has now children-categories.
    '''
    categories = category_name[:-1].split('/')
    deepest_cat = categories[-1:][0]
    parent_cat = categories[:-1]

    count=1
    parent_cat.reverse() 
    #generate parent joins for filer query
    filer_dict={'translations__slug':deepest_cat}
    for parent in parent_cat:
        str=''
        for i in xrange(0,count):
            str+='parent'
            if i< count-1: str+='__'
        count+=1
        str+='__translations__slug'
        filer_dict[str]=parent


    extra_context = getattr(kwargs, 'extra_context', {}) 
    if not category_name:
        #toplevel category list
        queryset = Category.objects.filter(level=0)
    else:

        category = Category.objects.get(**filer_dict)
        extra_context['curr_category']=category
        #if category.get_children().count()>0:
            #list sub categorie s
        from django.db.models import Count, Q

        queryset = category.get_children()#.annotate(entry_count=Count('blogpost')).annotate(child_count=Count('children')).filter(~Q(child_count=0)| ~Q(entry_count=0) )
        #queryset = category.get_children().annotate(entry_count=Count('blogpost')).filter(entry_count__gt=0)
        #else:
        #list entries of category
        try:
            language_code = request._feincms_page.language
            extra_context['entry_list'] = Entry.objects.active().filter(language=language_code)
        except (AttributeError, FieldError):
            extra_context['entry_list']=Entry.objects.active().filter(categories__id =category.id)
        #queryset = Entry.objects.active().filter(language=language_code)
        #template_name = entry_template_name

    return list_detail.object_list(
            request,
            queryset=queryset,
            template_name=template_name,
            extra_context=extra_context,
            **kwargs)


