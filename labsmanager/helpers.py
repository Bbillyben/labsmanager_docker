
"""  Credit : Inventree https://github.com/inventree/InvenTree """
import io
from wsgiref.util import FileWrapper
from django.http import StreamingHttpResponse


def DownloadFile(data, filename, content_type='application/text', inline=False) -> StreamingHttpResponse:
    """Create a dynamic file for the user to download.
    Args:
        data: Raw file data (string or bytes)
        filename: Filename for the file download
        content_type: Content type for the download
        inline: Download "inline" or as attachment? (Default = attachment)
    Return:
        A StreamingHttpResponse object wrapping the supplied data
    """
    filename = WrapWithQuotes(filename)

    if type(data) == str:
        wrapper = FileWrapper(io.StringIO(data))
    else:
        wrapper = FileWrapper(io.BytesIO(data))

    response = StreamingHttpResponse(wrapper, content_type=content_type)
    response['Content-Length'] = len(data)

    disposition = "inline" if inline else "attachment"

    response['Content-Disposition'] = f'{disposition}; filename={filename}'

    return response

def WrapWithQuotes(text, quote='"'):
    """Wrap the supplied text with quotes.
    Args:
        text: Input text to wrap
        quote: Quote character to use for wrapping (default = "")
    Returns:
        Supplied text wrapped in quote char
    """
    if not text.startswith(quote):
        text = quote + text

    if not text.endswith(quote):
        text = text + quote

    return text