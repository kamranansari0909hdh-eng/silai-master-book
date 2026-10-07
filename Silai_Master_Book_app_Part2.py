# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    st.header("📊 Dashboard")

    cs = customers()
    os = orders()

    total = sum(total_bill(o["id"]) for o in os)
    paid = sum(total_paid(o["id"]) for o in os)

    pending = sum(o["status"] == "Pending" for o in os)
    progress = sum(o["status"] == "In Progress" for o in os)
    completed = sum(o["status"] == "Completed" for o in os)

    a, b, c, d = st.columns(4)
    a.metric("Customers", len(cs))
    b.metric("Total Bills", len(os))
    c.metric("Pending", pending)
    d.metric("Completed", completed)

    a, b, c = st.columns(3)
    a.metric("Total Billing", money(total))
    b.metric("Payments Received", money(paid))
    c.metric("Balance Due", money(total - paid))

    st.divider()

    if os:
        st.subheader("📅 Recent Orders")
        rows = []
        for o in os[:10]:
            bill = total_bill(o["id"])
            pay = total_paid(o["id"])
            rows.append({
                "Order #": o["id"],
                "Customer": o["customer_name"],
                "Delivery": o["delivery_date"] or "-",
                "Status": o["status"],
                "Bill": money(bill),
                "Paid": money(pay),
                "Balance": money(bill - pay),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No orders yet. Create your first multi-item bill.")


# ============================================================
# CUSTOMERS
# ============================================================

elif page == "Customers":
    st.header("👤 Customer Management")

    tab1, tab2, tab3 = st.tabs([
        "➕ Add Customer",
        "✏️ Update Customer",
        "📋 Customer List",
    ])

    with tab1:
        with st.form("add_customer"):
            name = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number")
            address = st.text_area("Address")
            notes = st.text_area("Customer Notes")

            if st.form_submit_button("Save Customer", type="primary"):
                if not name.strip():
                    st.error("Customer name is required.")
                else:
                    cid = add_customer(name, phone, address, notes)
                    st.success(f"Customer saved. ID: {cid}")

    cs = customers()

    with tab2:
        if not cs:
            st.info("Add a customer first.")
        else:
            cid = st.selectbox(
                "Select Customer",
                [c["id"] for c in cs],
                format_func=lambda x: customer_label(customer(x)),
            )
            c = customer(cid)

            with st.form("update_customer"):
                name = st.text_input("Customer Name *", value=c["name"])
                phone = st.text_input("Phone Number", value=c["phone"] or "")
                address = st.text_area("Address", value=c["address"] or "")
                notes = st.text_area("Customer Notes", value=c["notes"] or "")

                if st.form_submit_button("Update Customer", type="primary"):
                    if not name.strip():
                        st.error("Name is required.")
                    else:
                        update_customer(cid, name, phone, address, notes)
                        st.success("Customer updated.")
                        st.rerun()

    with tab3:
        if cs:
            st.dataframe(
                pd.DataFrame([
                    {
                        "ID": c["id"],
                        "Name": c["name"],
                        "Phone": c["phone"],
                        "Address": c["address"],
                    }
                    for c in cs
                ]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No customers saved.")


# ============================================================
# NEW BILL
# ============================================================

elif page == "New Bill":
    st.header("🧾 New Bill — Multiple Clothes")

    cs = customers()

    if not cs:
        st.warning("Please add a customer first.")
    else:
        cid = st.selectbox(
            "Customer",
            [c["id"] for c in cs],
            format_func=lambda x: customer_label(customer(x)),
        )

        st.info(
            "You can add multiple clothes in the SAME bill. "
            "Each cloth can have its own quantity, price, description, "
            "measurements and design photo."
        )

        if "new_bill_items" not in st.session_state:
            st.session_state.new_bill_items = []

        # Add item form
        with st.expander("➕ Add Cloth / Item", expanded=True):
            item_name = st.text_input(
                "Cloth / Item Name",
                placeholder="Example: Blouse, Kurti, Salwar, Pant",
                key="new_item_name",
            )

            q1, q2 = st.columns(2)
            with q1:
                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=1,
                    step=1,
                    key="new_item_qty",
                )
            with q2:
                price = st.number_input(
                    "Price per piece (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=50.0,
                    key="new_item_price",
                )

            description = st.text_area(
                "Design / Stitching Details",
                key="new_item_description",
            )

            uploaded = st.file_uploader(
                "Design Photo (optional)",
                type=["jpg", "jpeg", "png", "webp"],
                key="new_item_photo",
            )

            st.markdown("**📏 Measurements for this item**")
            cols = st.columns(3)
            measurements = {}

            for i, field in enumerate(MEASUREMENT_FIELDS):
                with cols[i % 3]:
                    if field == "Other Notes":
                        measurements[field] = st.text_area(
                            field,
                            key=f"new_measure_{field}",
                        )
                    else:
                        measurements[field] = st.text_input(
                            field,
                            key=f"new_measure_{field}",
                            placeholder="Example: 36",
                        )

            if st.button("➕ Add This Item To Bill", type="primary"):
                if not item_name.strip():
                    st.error("Enter the cloth/item name.")
                else:
                    temp_name = safe_filename(item_name)
                    design_file = save_design(uploaded, temp_name)

                    st.session_state.new_bill_items.append({
                        "item_name": item_name,
                        "quantity": quantity,
                        "price": price,
                        "description": description,
                        "measurements": measurements,
                        "design_file": design_file,
                    })

                    st.success("Item added to this bill.")

        # Show current bill items
        st.divider()
        st.subheader(
            f"🧾 Current Bill — {len(st.session_state.new_bill_items)} item(s)"
        )

        if st.session_state.new_bill_items:
            grand_total = 0.0

            for i, item in enumerate(
                st.session_state.new_bill_items, start=1
            ):
                amount = item["quantity"] * item["price"]
                grand_total += amount

                with st.expander(
                    f"{i}. {item['item_name']} × {item['quantity']} — {money(amount)}",
                    expanded=False,
                ):
                    st.write(f"**Details:** {item['description'] or '-'}")

                    filled = {
                        k: v
                        for k, v in item["measurements"].items()
                        if str(v).strip()
                    }

                    if filled:
                        st.write("**Measurements:**")
                        st.dataframe(
                            pd.DataFrame(
                                [{"Measurement": k, "Value": v}
                                 for k, v in filled.items()]
                            ),
                            hide_index=True,
                            use_container_width=True,
                        )

                    if item["design_file"]:
                        st.image(
                            item["design_file"],
                            caption="Selected Design",
                            width=220,
                        )

                    if st.button(
                        f"Remove Item #{i}",
                        key=f"remove_item_{i}",
                    ):
                        st.session_state.new_bill_items.pop(i - 1)
                        st.rerun()

            st.success(f"Grand Total: {money(grand_total)}")

            st.subheader("📅 Bill Details")

            delivery = st.date_input(
                "Delivery Date",
                value=date.today(),
                key="bill_delivery",
            )

            status = st.selectbox(
                "Order Status",
                STATUSES,
                key="bill_status",
            )

            order_notes = st.text_area(
                "Overall Order Notes",
                key="bill_notes",
            )

            if st.button("💾 Create Complete Bill", type="primary"):
                order_id = create_order(
                    cid,
                    delivery,
                    status,
                    order_notes,
                    st.session_state.new_bill_items,
                )

                # The first payment is intentionally NOT automatically
                # inserted here. It is added through Payment History so
                # every payment has a date/method/note.
                st.session_state.new_bill_items = []

                st.success(f"Bill created successfully! Order #{order_id}")

                st.markdown(
                    f"### 📱 WhatsApp\n"
                    f"[Open WhatsApp Bill Message]("
                    f"{whatsapp_url(customer(cid)['phone'], build_whatsapp_message(order_id))}"
                    f")"
                    if whatsapp_url(customer(cid)['phone'], build_whatsapp_message(order_id))
                    else "Customer phone number is missing, so WhatsApp link cannot be generated."
                )

        else:
            st.info("No items added yet. Add the first cloth above.")


# ============================================================
# ORDERS & PAYMENTS
# ============================================================

elif page == "Orders & Payments":
    st.header("📦 Orders, Bills & Payment History")

    os = orders()

    if not os:
        st.info("No orders found.")
    else:
        search = st.text_input(
            "🔎 Search order/customer/item",
            placeholder="Example: Sana, Blouse, 12",
        )

        filtered = []
        q = search.strip().lower()

        for o in os:
            if (
                not q
                or q in str(o["id"]).lower()
                or q in o["customer_name"].lower()
                or q in (o["customer_phone"] or "").lower()
                or any(
                    q in item["item_name"].lower()
                    for item in order_items(o["id"])
                )
            ):
                filtered.append(o)

        if not filtered:
            st.warning("No matching orders.")
        else:
            order_id = st.selectbox(
                "Select Order",
                [o["id"] for o in filtered],
                format_func=lambda oid: (
                    f"Order #{oid} — "
                    f"{next(o['customer_name'] for o in filtered if o['id'] == oid)}"
                ),
            )

            o = order(order_id)
            items = order_items(order_id)
            pays = payments(order_id)

            total = total_bill(order_id)
            paid = total_paid(order_id)
            balance = total - paid

            a, b, c = st.columns(3)
            a.metric("Bill Total", money(total))
            b.metric("Paid", money(paid))
            c.metric("Balance Due", money(balance))

            st.divider()

            st.subheader("🧾 Bill Items")

            item_rows = []
            for i in items:
                item_rows.append({
                    "Item": i["item_name"],
                    "Qty": i["quantity"],
                    "Price": money(i["price"]),
                    "Amount": money(i["quantity"] * i["price"]),
                    "Description": i["description"] or "",
                    "Design": "Yes" if i["design_file"] else "No",
                })

            st.dataframe(
                pd.DataFrame(item_rows),
                use_container_width=True,
                hide_index=True,
            )

            # Status update
            c1, c2 = st.columns(2)

            with c1:
                new_status = st.selectbox(
                    "Order Status",
                    STATUSES,
                    index=STATUSES.index(o["status"]),
                )

                if st.button("Update Status"):
                    update_order_status(order_id, new_status)
                    st.success("Status updated.")
                    st.rerun()

            with c2:
                st.write(f"**Delivery:** {o['delivery_date'] or '-'}")
                st.write(f"**Customer:** {o['customer_name']}")
                st.write(f"**Phone:** {o['customer_phone'] or '-'}")

            st.divider()

            # Payment history
            st.subheader("💰 Payment History")

            if pays:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "Date": p["payment_date"],
                            "Method": p["method"],
                            "Amount": money(p["amount"]),
                            "Note": p["note"] or "",
                        }
                        for p in pays
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No payment recorded yet.")

            with st.form("add_payment"):
                p1, p2 = st.columns(2)

                with p1:
                    amount = st.number_input(
                        "Payment Amount (₹)",
                        min_value=0.0,
                        max_value=max(balance, 0.0),
                        value=0.0,
                        step=50.0,
                    )
                    payment_date = st.date_input(
                        "Payment Date",
                        value=date.today(),
                    )

                with p2:
                    method = st.selectbox(
                        "Payment Method",
                        ["Cash", "UPI", "Bank Transfer", "Card", "Other"],
                    )
                    note = st.text_input(
                        "Payment Note",
                        placeholder="Example: Advance / second payment / final",
                    )

                if st.form_submit_button("➕ Add Payment", type="primary"):
                    if amount <= 0:
                        st.error("Enter a payment amount.")
                    elif amount > balance:
                        st.error(
                            f"Payment cannot exceed current balance of {money(balance)}."
                        )
                    else:
                        add_payment(
                            order_id,
                            amount,
                            payment_date,
                            method,
                            note,
                        )
                        st.success("Payment added to history.")
                        st.rerun()

            st.divider()

            # WhatsApp
            st.subheader("📱 WhatsApp Bill Sharing")
            wa = whatsapp_url(
                o["customer_phone"],
                build_whatsapp_message(order_id),
            )

            if wa:
                st.markdown(
                    f"[📲 Open WhatsApp with complete bill message]({wa})"
                )
            else:
                st.warning(
                    "Customer phone number is missing. Add a phone number in Customers."
                )

            # Printable bill
            st.subheader("🖨️ Printable Bill")
            html = bill_html(order_id)

            st.download_button(
                "⬇️ Download Printable Bill (HTML)",
                data=html.encode("utf-8"),
                file_name=f"silai_master_book_order_{order_id}.html",
                mime="text/html",
            )

            with st.expander("Preview Bill"):
                st.components.v1.html(html, height=750, scrolling=True)


# ============================================================
# MEASUREMENTS
# ============================================================

elif page == "Measurements":
    st.header("📏 Saved Measurements")

    cs = customers()

    if not cs:
        st.warning("Add a customer first.")
    else:
        cid = st.selectbox(
            "Customer",
            [c["id"] for c in cs],
            format_func=lambda x: customer_label(customer(x)),
        )

        os = [o for o in orders() if o["customer_id"] == cid]

        if not os:
            st.info(
                "Measurements are saved per cloth inside each bill. "
                "Create a bill with an item to record its measurements."
            )
        else:
            oid = st.selectbox(
                "Select Order",
                [o["id"] for o in os],
                format_func=lambda x: (
                    f"Order #{x} — "
                    f"{next(o['delivery_date'] for o in os if o['id'] == x) or '-'}"
                ),
            )

            its = order_items(oid)

            for i, item in enumerate(its, 1):
                st.subheader(
                    f"{i}. {item['item_name']} × {item['quantity']}"
                )

                m = load_measurements(item)
                filled = [
                    {"Measurement": k, "Value": v}
                    for k, v in m.items()
                    if str(v).strip()
                ]

                if filled:
                    st.dataframe(
                        pd.DataFrame(filled),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("No measurements entered for this item.")

                st.divider()


# ============================================================
# DESIGN GALLERY
# ============================================================

elif page == "Design Gallery":
    st.header("🖼️ Design Gallery")

    os = orders()

    if not os:
        st.info("No design photos saved yet.")
    else:
        all_designs = []

        for o in os:
            for item in order_items(o["id"]):
                if item["design_file"] and Path(item["design_file"]).exists():
                    all_designs.append({
                        "order_id": o["id"],
                        "customer": o["customer_name"],
                        "item": item["item_name"],
                        "path": item["design_file"],
                    })

        if not all_designs:
            st.info("No design photos found.")
        else:
            for start in range(0, len(all_designs), 3):
                cols = st.columns(3)

                for col, d in zip(cols, all_designs[start:start + 3]):
                    with col:
                        st.image(
                            d["path"],
                            caption=(
                                f"Order #{d['order_id']} • "
                                f"{d['customer']} • {d['item']}"
                            ),
                            use_container_width=True,
                        )


st.divider()
st.caption(
    "Silai Master Book • SQLite persistence • "
    "Keep backups of the database and design_gallery folder."
)
