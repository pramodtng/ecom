from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import json
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_migrate import Migrate
import secrets


app = Flask(__name__)
secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SECRET_KEY'] = secret_key
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class RemoveFromCartForm(FlaskForm):
    submit = SubmitField('Remove')


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=0)
    product = db.relationship('Product', back_populates='carts')
    product_title = db.Column(db.String(100))
    product_price = db.Column(db.String(20))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    price = db.Column(db.String(20))
    image = db.Column(db.String(200))
    description = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=0)
    carts = db.relationship('Cart', back_populates='product')


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=0)
    product = db.relationship('Product')


class CheckoutForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])


class OrderDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.String(100), nullable=False)
    address2 = db.Column(db.String(100))
    payment_method = db.Column(db.String(100), nullable=False)
    name_on_card = db.Column(db.String(100), nullable=False)
    cc_number = db.Column(db.String(16), nullable=False)
    product_title = db.Column(db.String(100))
    product_price = db.Column(db.Float)


@app.route('/checkout', methods=['POST'])
def checkout():
    first_name = request.form.get('firstName')
    last_name = request.form.get('lastName')
    email = request.form.get('email')
    address = request.form.get('address')
    address2 = request.form.get('address2')
    payment_method = request.form.get('paymentMethod')
    name_on_card = request.form.get('cc-name')
    cc_number = request.form.get('cc-number')

    product_title = request.form.get('productTitle')
    product_price = request.form.get('productPrice')

    print(product_title, product_price)
    if product_title is None:

        product_title = ""

    if product_price is not None:
        product_price = float(product_price)
    else:

        product_price = 0.0

    order_details = OrderDetails(
        first_name=first_name,
        last_name=last_name,
        email=email,
        address=address,
        address2=address2,
        payment_method=payment_method,
        name_on_card=name_on_card,
        cc_number=cc_number,
        product_title=product_title,
        product_price=product_price
    )

    db.session.add(order_details)
    db.session.commit()

    return render_template('success_message.html', message="Order placed successfully!", )


def populate_database():
    with open('products.json') as file:
        data = json.load(file)
        products = data['products']

        for product in products:
            existing_product = Product.query.filter_by(
                title=product['title']).first()

            if not existing_product:
                new_product = Product(
                    title=product['title'],
                    price=product['price'],
                    image=product['image'],
                    description=product['description'],
                    quantity=product['quantity'] if 'quantity' in product else 0
                )
                db.session.add(new_product)

        db.session.commit()


@app.route('/populate-database')
def populate_database_route():
    populate_database()
    return 'Database populated successfully'


@app.route('/')
def index():
    search_query = request.args.get('q')

    if search_query:
        products = Product.query.filter(
            Product.title.ilike(f'%{search_query}%')).all()
    else:
        products = Product.query.all()
    cart_items = Cart.query.filter(Cart.quantity > 0).all()
    cart_count = sum([item.quantity for item in cart_items])
    return render_template('index.html', products=products, cart_count=cart_count)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get(product_id)

    if product:
        cart_items = Cart.query.filter(Cart.quantity > 0).all()
        cart_count = sum([item.quantity for item in cart_items])
        return render_template('product_details.html', product=product, cart_count=cart_count)

    return "Product not found"


@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get(product_id)

    if product is None:
        return redirect(url_for('index'))

    cart_item = Cart.query.filter_by(product_id=product_id).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(product=product, quantity=1)
        db.session.add(cart_item)

    db.session.commit()

    order = Order(product=product, quantity=1)
    db.session.add(order)
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/cartpage')
def cart_page():
    cart_items = Cart.query.filter(Cart.quantity > 0).all()
    cart_count = sum([item.quantity for item in cart_items])
    return render_template('cart_page.html', cart_items=cart_items, cart_count=cart_count)


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart_item = Cart.query.filter_by(product_id=product_id).first()

    if cart_item:
        cart_item.quantity -= 1

        if cart_item.quantity == 0:
            db.session.delete(cart_item)

        db.session.commit()

    return redirect(url_for('cart_page'))


@app.route('/checkout-page', methods=['GET', 'POST'])
def checkout_page():
    form = CheckoutForm()

    if form.validate_on_submit():
        email = form.email.data

        # Process the order and update the database
        cart_items = Cart.query.filter(Cart.quantity > 0).all()
        if cart_items:
            for cart_item in cart_items:
                product = cart_item.product
                product.quantity -= cart_item.quantity

                order = Order(product=product, quantity=cart_item.quantity)
                db.session.add(order)

                cart_item.quantity = 0

            db.session.commit()

            return render_template('order_confirmation.html', email=email)
        else:
            error_message = 'Your cart is empty. Please add some products before checking out.'
            return render_template('checkout_page.html', error_message=error_message, form=form)

    cart_items = Cart.query.filter(Cart.quantity > 0).all()
    cart_count = sum([item.quantity for item in cart_items])
    return render_template('checkout_page.html', form=form, cart_items=cart_items, cart_count=cart_count)


if __name__ == '__main__':
    app.run()
