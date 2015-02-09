from flask import (
    abort,
    flash,
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for,
    )
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.seasurf import SeaSurf
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.bcrypt import Bcrypt
from functools import wraps
from ..text import is_word, split_by_punctuation
from ..finnish_syllabifier import syllabify

app = Flask(__name__, static_folder='static')
app.config.from_pyfile('finnsyll_config.py')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

# To mirate database:
#     python finnsyll.py db init (only for initial migration)
#     python finnsyll.py db migrate
#     python finnsyll.py db upgrade

csrf = SeaSurf(app)
flask_bcrypt = Bcrypt(app)


# Models ----------------------------------------------------------------------

class Linguist(db.Model):
    __tablename__ = 'Mages'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = flask_bcrypt.generate_password_hash(password)

    def __repr__(self):
        return self.username

    def __unicode__(self):
        return self.__repr__()


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # the word's orthography
    orth = db.Column(db.String(40), nullable=False, unique=True)

    # the syllabification that is estimated programmatically
    test_syll = db.Column(db.String(40), default='')

    # the correct syllabification (hand-verified)
    syll = db.Column(db.String(40), default='')

    # an alternative syllabification (hand-verified)
    alt_syll = db.Column(db.String(40), default='')

    # the word's part-of-speech
    pos = db.Column(db.String(10), default='')

    # a list of the word's syllables
    syllables = db.Column(db.PickleType, default=[])

    # a list of the word's weights
    weights = db.Column(db.PickleType, default=[])

    # a list of the word's stresses
    stress = db.Column(db.PickleType, default=[])

    # a list of the word's alternative stresses
    alt_stress = db.Column(db.PickleType, default=[])

    # a list of the word's sonorities
    sonorities = db.Column(db.PickleType, default=[])

    # a boolean indicating if the word is a compound
    is_compound = db.Column(db.Boolean, default=False)

    # a boolean indicating if the word is a stopword -- only if the
    # word's syllabification is lexically marked
    is_stopword = db.Column(db.Boolean, default=False)

    # a boolean indicating if the algorithm has estimated correctly
    is_gold = db.Column(db.Boolean)

    def __init__(self, orth, syll=None, alt_syll=None):
        self.orth = orth

        if syll:
            self.syll = syll

        if alt_syll:
            self.alt_syll = alt_syll

        # populate self.test_syll
        self.syllabify()

    def __repr__(self):
        return '\tWord: %s\n\tEstimated syll: %s\n\tCorrect syll: %s\n\t' % (
            self.orth, self.test_syll or '', self.syll or '')

    def __unicode__(self):
        return self.__repr__()

    def update_gold(self):
        '''Compare test syllabifcation against true syllabification.

        Token.is_gold is True if the test syllabifcation matches the true
        syllabification. Otherwise, Token.is_fold is False.
        '''
        if self.test_syll and self.syll:
            is_gold = self.test_syll == self.syll

            if not is_gold and self.alt_syll:
                is_gold = self.test_syll == self.alt_syll

            self.is_gold = is_gold
            db.session.commit()

            return is_gold

        return False

    def syllabify(self):  # PLUG
        '''Algorithmically syllabify Token based on its orthography.'''
        # syllabifcations do not preserve capitalization
        token = self.orth.lower()
        self.test_syll = syllabify(token)

        if self.syll:
            self.update_gold()

    def correct(self, syll, alt_syll='', is_compound=False):
        '''Store correct syllabification and/or alternative syllabfication.'''
        self.syll = syll
        self.alt_syll = alt_syll
        self.is_compound = is_compound
        db.session.commit()

        self.update_gold()

    def syllable_count(self):
        '''Return the number of syllables the word contains.'''
        if self.is_gold:
            if self.syllables:
                return len(self.syllables)

            return self.syll.count('.') + 1


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # the entire text of the document
    text = db.Column(db.Text, nullable=False, unique=True)

    # a list of IDs for each word as they appear in the text
    token_IDs = db.Column(db.PickleType, default=[], editable=False)

    # the text as a pickled list, incl. Token IDs and punctuation strings
    pickled_text = db.Column(db.PickleType, default=[], editable=False)

    # a boolean indicating if all of the document's words have been reviewed
    reviewed = db.Column(db.Boolean, defualt=False)

    def __init__(self, filename):
        self.pickle(filename)

    def __repr__(self):
        return 'Text #%s' % self.id

    def __unicode__(self):
        return self.__repr__()

    def pickle(self, filename):
        '''Compile self.text, self.token_IDs, and self.picked_text.'''
        try:
            filename = 'fin.txt'

            f = open(filename, 'r')
            text = f.readlines()
            f.close()

            self.text = text

            for line in text:
                line = line.split(' ')

                for i in line:
                    tokens = split_by_punctuation(i)  # TODO: keep compounds!!

                    for t in tokens:

                        if is_word(t):
                            word = find_token(t)

                            if not word:
                                word = Token(word)
                                db.session.add(word)
                                db.session.commit()

                            self.token_IDs.append(word.id)  # CHECK -- int?
                            self.pickled_text.append(word.id)

                        if t:
                            self.pickled_text.append(t)

        except IOError:
            raise IOError('File %s could not be opened.' % filename)

    def query_tokens(self):
        '''Return query of Tokens, ordered as they appear in the text.'''
        query = Token.query

        for ID in self.token_IDs:
            query = query.union(Token.query.get(ID))

        return query

    def verify_all_unverified_tokens(self):
        '''For all of the text's unverified Tokens, set syll equal to test_syll.

        This function is intended for when all uverified Tokens have been
        correctly syllabified in test_syll. Proceed with caution.
        '''
        tokens = self.query_tokens()
        tokens = tokens.filter(is_gold=None)

        for token in tokens:
            token.correct(syll=token.test_syll)

        self.reviewed = True
        db.session.commit()

    def render_html(self):
        '''Return text as an html string to be rendered on the frontend.

        This html string includes a modal for each word in the text. Each modal
        contains a form that will allow Arto to edit the word's Token, i.e.,
        Token.syll, Token.alt_syll, and Token.is_compound.
        '''
        html = '<div class="doc-text">'

        modals = ''
        modal_count = 0

        for t in self.pickled_text:

            if isinstance(t, int):

                modal_count += 1

                word = Token.query.get(t)

                test_syll_class = self._get_test_syll_css_class(word)

                html += ' <a href="#modal-%s" class="word' % modal_count

                html += ' %s' % test_syll_class

                if word.is_compound:
                    html += ' compound'

                if word.alt_syll:
                    html += ' alt'

                html += '"" %s </a>' % t

                modals += self._create_modal(t, modal_count, test_syll_class)

            elif t == '\n':
                html += '<br>'

            else:
                html += '<div class="punct">%s</div>' % t.test_syll

        html += '</div>' + modals

        return html

    @staticmethod
    def _get_test_syll_css_class(token):
        # Return an is_gold css class for a given token.
        if token.is_gold:
            return 'good'

        elif token.is_gold is False:
            return 'bad'

        else:
            return 'unverified'

    @staticmethod
    def _create_modal(self, token, modal_count, test_syll_class):
        # http://codepen.io/maccadb7/pen/nbHEg?editors=110

        modal = '''
            <!-- Modal %s -->
            <div class="modal" id="modal-%s" aria-hidden="true">
              <div class="modal-dialog">

                <div class="modal-header">
                  <a href="#close" class="btn-close" aria-hidden="true">×</a>
                </div>

                <div class="modal-body">

                    <form class="tokens2" method="POST">
                        <input
                            type='hidden' name='_csrf_token'
                            value='{{ csrf_token() }}'>
                        <input
                            type='text' name='orth' class='orth'
                            value='%a' disabled='True' >
                        <p class='test_syll %s'>%s</p>
                        <input
                            type='text' name='syll'
                            placeholder='correct syll'
                            value='%s'>
                        <input
                            type='text' name='alt_syll'
                            placeholder='alternative syll'
                            value='%s'>
                        <span class='compound-label'>Compound</span>
                        <span>
                            <input type='checkbox' name='is_compound' value=1>
                        </span>
                        <input
                            type='submit' class='OK' value='OK!'>
                    </form>
                </div>


              </div>
            </div>
            <!-- /Modal -->
            ''' % (
                modal_count,
                modal_count,
                token.orth,
                test_syll_class,
                token.test_syll,
                token.syll if token.syll != token.test_syll else '',
                token.alt_syll,
            )

        return modal


# Database functions ----------------------------------------------------------

def delete_token(orth):
    '''Delete token (e.g., if the orthopgraphy is a misspelling).'''
    try:
        token = Token.query.filter_by(orth=orth).first()
        db.session.delete(token)
        db.session.commit()

    except KeyError:
        pass


def find_token(orth):
    '''Retrieve token by its ID.'''
    try:
        token = Token.query.filter_by(orth=orth).first()
        return token

    except KeyError:
        return None


def get_bad_tokens():
    '''Return all of the Tokens that are incorrectly syllabified.'''
    return Token.query.filter_by(is_gold=False).order_by(Token.orth)


def get_good_tokens():
    '''Return all of the Tokens that are correctly syllabified.'''
    return Token.query.filter_by(is_gold=True).order_by(Token.orth)


def get_unverified_tokens():
    '''Return Tokens with uncertain syllabifications.'''
    return Token.query.filter_by(is_gold=None)


def review_tokens():
    '''Compare test_syll and syll for all Tokens; update is_gold.'''
    tokens = Token.query.all()

    for token in tokens:
        token.update_gold()


def syllabify_tokens():
    '''Algorithmically syllabify all Tokens.

    This is done anytime a Token is instantiated. It *should* also be done
    anytime the syllabifying algorithm is updated.'''
    tokens = Token.query.all()

    for token in tokens:
        token.syllabify()


def get_unreviewed_documents():
    return Document.query.filter_by(reviewed=False)


# View helpers ----------------------------------------------------------------

@app.before_request
def renew_session():
    # Forgot why I did this... but I think it's important
    session.modified = True


def login_required(x):
    # View decorator requiring users to be authenticated to access the view
    @wraps(x)
    def decorator(*args, **kwargs):
        if session.get('current_user'):
            return x(*args, **kwargs)

        return redirect(url_for('login_view'))

    return decorator


def redirect_url(default='main_view'):
    # Redirect page to previous url or to main_view
    return request.referrer or url_for(default)


def apply_form(http_form):
    # Apply changes to Token instance based on POST request
    try:
        orth = http_form['orth']
        syll = http_form['syll']
        alt_syll = http_form['alt_syll'] or ''
        is_compound = bool(http_form['is_compound'])
        token = find_token(orth)
        token.correct(
            syll=syll,
            alt_syll=alt_syll,
            is_compound=is_compound
            )

    except (KeyError, LookupError):
        pass


# Views -----------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
@login_required
def main_view():
    '''List links to unverified texts (think: Table of Contents).'''
    docs = get_unreviewed_documents()
    return render_template('main.html', docs=docs, kw='main')


@app.route('/doc/<id>', methods=['GET', 'POST'])
@login_required
def doc_view(id):
    '''Present detail view of specified doc, composed of editable Tokens.'''
    doc = Token.query.get_or_404(id)

    if doc.reviewed:
        abort(404)

    if request.method == 'POST':
        apply_form(request.form)

    doc_id = doc.id
    doc = doc.render_html()

    return render_template('tokenized.html', doc=doc, doc_id=doc_id, kw='doc')


@app.route('/approve/approve/approve/doc/<id>', methods=['POST', ])
@login_required
def approve_doc_view(id):
    '''For all of the doc's unverified Tokens, set syll equal to test_syll.'''
    doc = Token.query.get_or_404(id)
    doc.verify_all_unverified_tokens()

    return redirect(url_for('main_view'))


@app.route('/unverified', methods=['GET', 'POST'])
@login_required
def unverified_view():
    '''List all unverified Tokens and process corrections.'''
    tokens = get_unverified_tokens()

    if request.method == 'POST':
        apply_form(request.form)

    return render_template('tokens.html', tokens=tokens, kw='unverified')


@app.route('/bad', methods=['GET', 'POST'])
@login_required
def bad_view():
    '''List all incorrectly syllabified Tokens and process corrections.'''
    tokens = get_bad_tokens()

    if request.method == 'POST':
        apply_form(request.form)

    return render_template('tokens.html', tokens=tokens, kw='bad')


@app.route('/good', methods=['GET', 'POST'])
@login_required
def good_view():
    '''List all correctly syllabified Tokens and process corrections.'''
    tokens = get_good_tokens()

    if request.method == 'POST':
        apply_form(request.form)

    return render_template('tokens.html', tokens=tokens, kw='good')


@app.route('/enter', methods=['GET', 'POST'])
def login_view():
    '''Sign in current user.'''
    if session.get('current_user'):
        return redirect(url_for('main_view'))

    if request.method == 'POST':
        username = request.form['username']
        linguist = Linguist.query.filter_by(username=username).first()

        if linguist is None or not flask_bcrypt.check_password_hash(
                linguist.password,
                request.form['password']
                ):
            flash('Invalid username and/or password.')

        else:
            session['current_user'] = linguist.username
            return redirect(url_for('main_view'))

    return render_template('enter.html')


@app.route('/leave')
def logout_view():
    '''Sign out current user.'''
    session.pop('current_user', None)
    return redirect(url_for('main_view'))


if __name__ == '__main__':
    manager.run()
