from datetime import date
from django.db.models.query import EmptyQuerySet 
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
      page = page,
      template_name = template_name,
      extra_context = extra_context,
      **kwargs)
   
def browse_entries(request, category_name='', year=None, month=None, day=None,
               paginate_by=10, template_name='blog/category_list.html', limit=None,page=0,
               language_code=None, wp_like=True, **kwargs):
    '''  
        Lets the user browse through the hierarchically blog categories.
        Shows sub categories and blog entries of given category-slug.

        @param category_name: category_slug would be a better name ;)
        @param wp_like: If True entries of sub-categories shown, too.
        @TODO year, month, day, limit are currently UNUSED!
        @TODO: maybe category listing should be  included in 
                Navigation extension.
    '''
    #generate parent joins for filer query
    categories = category_name[:-1].split('/')
    deepest_cat = categories[-1:][0]
    parent_cat = categories[:-1]

    count=1
    parent_cat.reverse() 
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
        extra_context['category_list'] = Category.objects.filter(level=0)
        queryset=EmptyQuerySet(Entry)
    else:
        category = Category.objects.get(**filer_dict)
        extra_context['curr_category']=category
        extra_context.update({ 'comments' : settings.BLOG_COMMENTS,})
        extra_context['category_list'] = category.get_children()

        #list entries of category
        filter_args  = {
            'categories__id': category.id,
        }
        if wp_like: # inspirated by wordpress
            # show entries of subcategories, too.
            descendants = category.get_descendants(include_self=True)
            cat_ids = [ d.id for d in descendants ]
            filter_args = {
                'categories__id__in': cat_ids,
            }

        if year:
            filter_args['published_on__year']=int(year)
            extra_context.update({'drilldown_mode': 'year', 'title' : _('entries of the year')})
        else:
            year = 1
        if month:
            filter_args['published_on__month']=int(month)
            extra_context.update({'drilldown_mode': 'month', 'title' : _('entries of the month')})
        else:
            month = 1
        if day:
            filter_args['published_on__day']=int(day)
            extra_context.update({'drilldown_mode': 'day', 'title' : _('entries of the year')})
        else:
            day = 1
        try:
            language_code = request._feincms_page.language
            filter_args['language']=language_code
            queryset = Entry.objects.active().filter(**filter_args)
        except (AttributeError, FieldError):
            queryset=Entry.objects.active().filter(**filter_args)

        extra_context.update({'date':date(int(year), int(month), int(day))})

        if limit:
            queryset = queryset[:limit]

    if settings.BLOG_LIST_PAGINATION:
        paginate_by = settings.BLOG_LIST_PAGINATION
    return list_detail.object_list(
            request,
            queryset=queryset,
            page=page,
            paginate_by = paginate_by,
            template_name=template_name,
            extra_context=extra_context,
            **kwargs)


def entries_by_tag(request, tag='', template_name="blog/entry_list_tagged.html",
                    paginate_by=10, page=0, **kwargs):
    if tag:
        tag =  tag[:-1] #remove slash of the end
        try:
            language_code = request._feincms_page.language
            queryset=Entry.objects.active().filter(language=language_code, tags__icontains=tag)
        except (AttributeError, FieldError):
            queryset=Entry.objects.active().filter(tags__icontains=tag)
    else:
        queryset=Entry.objects.active()

    if settings.BLOG_LIST_PAGINATION:
        paginate_by=settings.BLOG_LIST_PAGINATION
    extra_context={}
    extra_context["tag"]=tag

    return list_detail.object_list(
                request,
                queryset=queryset,
                page=page,
                paginate_by=paginate_by,
                template_name=template_name,
                extra_context=extra_context,
                **kwargs)
